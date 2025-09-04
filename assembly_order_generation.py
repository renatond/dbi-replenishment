import streamlit as st
import pandas as pd
import numpy as np
import math

def calculate_sales_velocity(sales_df):
    """Calculate average daily sales from 6 months of data"""
    if sales_df is None or len(sales_df) == 0:
        return pd.DataFrame(columns=['SKU', 'avg_daily_sales', 'avg_monthly_sales'])
    
    # Debug: Show what data we're working with
    # st.write(f"**Sales velocity calculation input:**")
    # st.write(f"- DataFrame shape: {sales_df.shape}")
    # st.write(f"- Columns: {list(sales_df.columns)}")
    
    # Get the first column as SKU column
    sku_col = sales_df.columns[0]
    
    # Get sales columns (exclude SKU column and Total/Average columns)
    sales_columns = [col for col in sales_df.columns if col != sku_col and not col.startswith('Total') and not col.startswith('Average')]
    # st.write(f"- Using columns for calculation: {sales_columns}")
    
    result_df = sales_df.copy()
    
    # CRITICAL: Convert SKU column to string for consistent matching
    result_df[sku_col] = result_df[sku_col].astype(str)
    
    # Calculate total sales for 6 months
    result_df['total_6_months'] = result_df[sales_columns].sum(axis=1, skipna=True)
    
    # Calculate average daily sales: total ÷ 6 months ÷ 30 days
    result_df['avg_daily_sales'] = result_df['total_6_months'] / 6 / 30
    
    # Calculate average monthly sales: total ÷ 6 months
    result_df['avg_monthly_sales'] = result_df['total_6_months'] / 6
    
    result_df_final = result_df[[sku_col, 'avg_daily_sales', 'avg_monthly_sales']].rename(columns={sku_col: 'SKU'})
    
    # Ensure SKU column is string in final result
    result_df_final['SKU'] = result_df_final['SKU'].astype(str)
    
    return result_df_final

def calculate_inventory_position(availability_df, sku, locations=['NC - Main', 'NC - Armory', 'NC - FFL']):
    """Calculate total inventory position for a SKU across specified locations"""
    if availability_df is None or len(availability_df) == 0:
        return {'on_hand': 0, 'on_order': 0, 'in_transit': 0, 'total_available': 0}
    
    # Use the exact column names from the Availability Report
    sku_col = 'SKU'
    location_col = 'Location'
    on_hand_col = 'OnHand'
    on_order_col = 'OnOrder'
    in_transit_col = 'InTransit'
    
    # Check if required columns exist
    missing_cols = []
    for col_name, col_var in [('SKU', sku_col), ('Location', location_col), ('OnHand', on_hand_col)]:
        if col_var not in availability_df.columns:
            missing_cols.append(col_name)
    
    if missing_cols:
        st.warning(f"Missing columns in Availability Report: {missing_cols}")
        return {'on_hand': 0, 'on_order': 0, 'in_transit': 0, 'total_available': 0}
    
    # CRITICAL: Convert SKU columns to string for consistent matching
    availability_df_copy = availability_df.copy()
    availability_df_copy[sku_col] = availability_df_copy[sku_col].astype(str)
    sku = str(sku)  # Ensure the input SKU is also a string
    
    # Filter for the specific SKU
    sku_data = availability_df_copy[availability_df_copy[sku_col] == sku]
    
    if len(sku_data) == 0:
        return {'on_hand': 0, 'on_order': 0, 'in_transit': 0, 'total_available': 0}
    
    # Filter for specified locations
    location_data = sku_data[sku_data[location_col].isin(locations)]
    
    on_hand = location_data[on_hand_col].sum() if on_hand_col in location_data.columns else 0
    on_order = location_data[on_order_col].sum() if on_order_col in location_data.columns else 0
    in_transit = location_data[in_transit_col].sum() if in_transit_col in location_data.columns else 0
    
    return {
        'on_hand': on_hand,
        'on_order': on_order, 
        'in_transit': in_transit,
        'total_available': on_hand + on_order + in_transit
    }

def get_replenish_skus(bom_df, inventory_df, availability_df, sales_velocity_df, warehouse='NC'):
    """Identify SKUs that need replenishment based on business rules"""
    
    if any(df is None or len(df) == 0 for df in [bom_df, inventory_df, availability_df, sales_velocity_df]):
        return pd.DataFrame()
    
    # Use the exact column names from the Inventory List
    sku_col = 'ProductCode'  # SKU is called ProductCode in Inventory List
    assembly_bom_col = 'AssemblyBOM'
    auto_assembly_col = 'AutoAssemble'
    auto_disassembly_col = 'AutoDisassemble'
    
    # Check if required columns exist
    missing_cols = []
    for col_name, col_var in [('ProductCode', sku_col), ('AssemblyBOM', assembly_bom_col), 
                              ('AutoAssemble', auto_assembly_col), ('AutoDisassemble', auto_disassembly_col)]:
        if col_var not in inventory_df.columns:
            missing_cols.append(col_name)
    
    if missing_cols:
        st.warning(f"Missing columns in Inventory List: {missing_cols}")
        return pd.DataFrame()
    
    # Filter eligible SKUs from inventory list
    try:
        # CRITICAL: Convert all relevant columns to string for consistent matching
        inventory_df_copy = inventory_df.copy()
        inventory_df_copy[sku_col] = inventory_df_copy[sku_col].astype(str)
        inventory_df_copy[assembly_bom_col] = inventory_df_copy[assembly_bom_col].astype(str)
        inventory_df_copy[auto_assembly_col] = inventory_df_copy[auto_assembly_col].astype(str)
        inventory_df_copy[auto_disassembly_col] = inventory_df_copy[auto_disassembly_col].astype(str)
        
        eligible_skus_filter = (
            (inventory_df_copy[assembly_bom_col].str.upper() == 'YES') &
            (inventory_df_copy[auto_assembly_col].str.upper() == 'NO') &
            (inventory_df_copy[auto_disassembly_col].str.upper() == 'NO') &
            (~inventory_df_copy[sku_col].isin(['2444', '4300', '3818', '2582']))
        )
        
        eligible_skus = inventory_df_copy[eligible_skus_filter][sku_col].unique()
            
    except Exception as e:
        st.error(f"Error filtering eligible SKUs: {str(e)}")
        st.exception(e)
        return pd.DataFrame()
    
    replenish_list = []
    
    for sku in eligible_skus:
        # CRITICAL: Ensure SKU is string for consistent matching
        sku = str(sku)
        
        # Get inventory position for the specific warehouse
        if warehouse == 'NC':
            locations = ['NC - Main', 'NC - Armory', 'NC - FFL']
        else:  # CA
            locations = ['CA - Main', 'CA - Armory', 'CA - FFL']
        
        inv_position = calculate_inventory_position(availability_df, sku, locations)
        
        # Get sales velocity (ensure string matching)
        sales_data = sales_velocity_df[sales_velocity_df['SKU'] == sku]
        avg_daily_sales = sales_data['avg_daily_sales'].iloc[0] if len(sales_data) > 0 else 0
        avg_monthly_sales = sales_data['avg_monthly_sales'].iloc[0] if len(sales_data) > 0 else 0
        
        # Default days of stock
        days_of_stock = 30  # Default value
        
        # Calculate replenishment need
        target_inventory = avg_daily_sales * days_of_stock
        replenishment_qty = max(0, target_inventory - inv_position['total_available'])
        
        # Check if this SKU needs replenishment (using business logic from Analysis tab)
        available_in_warehouse = inv_position['total_available']
        needs_replenishment = (available_in_warehouse + inv_position['on_order']) < avg_monthly_sales
        
        if needs_replenishment and replenishment_qty > 0:
            # Calculate quantity for assembly with reasonable bounds
            # Round UP the difference as per google_sheets_rules.md line 82
            base_calculation = avg_monthly_sales - available_in_warehouse
            base_qty = max(2, math.ceil(base_calculation)) if base_calculation > 0 else 2
            
            # Apply reasonable limits based on monthly sales velocity
            # Cap at 3x monthly sales to prevent unrealistic quantities
            max_reasonable_qty = max(10, math.ceil(avg_monthly_sales * 3))
            
            # Also consider a hard cap for very high-velocity items
            absolute_max = 1000  # No single assembly order should exceed 1000 units
            
            qty_for_assembly = min(base_qty, max_reasonable_qty, absolute_max)
            
            replenish_list.append({
                'SKU': str(sku),  # Ensure SKU is stored as string
                'avg_daily_sales': avg_daily_sales,
                'avg_monthly_sales': avg_monthly_sales,
                'available_in_warehouse': available_in_warehouse,
                'warehouse': warehouse,
                'on_order': inv_position['on_order'],
                'target_inventory': target_inventory,
                'qty_for_assembly': qty_for_assembly
            })
    
    return pd.DataFrame(replenish_list)

def analyze_assembly_status(bom_df, availability_df, replenish_df, warehouse='NC'):
    """Analyze assembly feasibility for replenishment SKUs"""
    
    if any(df is None or len(df) == 0 for df in [bom_df, availability_df, replenish_df]):
        return []
    
    # Use the exact column names from the BOM Report
    product_sku_col = 'Product SKU'
    product_name_col = 'Product'
    component_sku_col = 'Component SKU'
    component_name_col = 'Component'
    quantity_col = 'Quantity'
    
    # Check if required columns exist
    missing_cols = []
    for col_name, col_var in [('Product SKU', product_sku_col), ('Component SKU', component_sku_col), 
                              ('Quantity', quantity_col)]:
        if col_var not in bom_df.columns:
            missing_cols.append(col_name)
    
    if missing_cols:
        st.warning(f"Missing columns in BOM Report: {missing_cols}")
        return []
    
    assembly_analysis = []
    
    for _, replenish_row in replenish_df.iterrows():
        assembly_sku = str(replenish_row['SKU'])  # Ensure string
        qty_needed = replenish_row['qty_for_assembly']
        
        # CRITICAL: Convert BOM Product SKU column to string for matching
        bom_df_copy = bom_df.copy()
        bom_df_copy[product_sku_col] = bom_df_copy[product_sku_col].astype(str)
        bom_df_copy[component_sku_col] = bom_df_copy[component_sku_col].astype(str)
        
        # Get BOM components for this assembly
        assembly_components = bom_df_copy[bom_df_copy[product_sku_col] == assembly_sku]
        
        if len(assembly_components) == 0:
            continue
            
        assembly_feasible = True
        component_analysis = []
        
        for _, component in assembly_components.iterrows():
            component_sku = str(component[component_sku_col])  # Ensure string
            qty_per_assembly = component[quantity_col]
            total_component_needed = qty_per_assembly * qty_needed
            
            # Get component inventory in warehouse locations
            if warehouse == 'NC':
                locations = ['NC - Main', 'NC - Armory', 'NC - FFL']
            else:  # CA
                locations = ['CA - Main', 'CA - Armory', 'CA - FFL']
            
            component_inv = calculate_inventory_position(availability_df, component_sku, locations)
            
            component_status = "Ready" if component_inv['total_available'] >= total_component_needed else "Shortage"
            if component_status == "Shortage":
                assembly_feasible = False
            
            component_analysis.append({
                'component_sku': component_sku,
                'component_name': component.get(component_name_col, '') if component_name_col else '',
                'qty_per_assembly': qty_per_assembly,
                'total_needed': total_component_needed,
                'available': component_inv['total_available'],
                'shortage': max(0, total_component_needed - component_inv['total_available']),
                'status': component_status
            })
        
        assembly_analysis.append({
            'assembly_sku': assembly_sku,
            'assembly_name': assembly_components.iloc[0].get(product_name_col, '') if product_name_col else '',
            'qty_for_assembly': qty_needed,
            'assembly_status': "Ready for Production" if assembly_feasible else "Cannot Assemble",
            'avg_daily_sales': replenish_row['avg_daily_sales'],
            'avg_monthly_sales': replenish_row['avg_monthly_sales'],
            'available_in_warehouse': replenish_row['available_in_warehouse'],
            'warehouse': replenish_row['warehouse'],
            'components': component_analysis,
            'total_components': len(component_analysis),
            'ready_components': len([c for c in component_analysis if c['status'] == 'Ready'])
        })
    
    return assembly_analysis

def generate_transfer_recommendations(availability_df, bom_df, warehouse='NC'):
    """Generate recommendations for transfers between warehouse locations based on business logic"""
    
    if availability_df is None or len(availability_df) == 0:
        return []
    
    transfer_recommendations = []
    
    # Use exact column names from Availability Report
    sku_col = 'SKU'
    location_col = 'Location'
    on_hand_col = 'OnHand'
    product_name_col = 'ProductName'
    
    # Check if required columns exist
    required_cols = [sku_col, location_col, on_hand_col]
    if not all(col in availability_df.columns for col in required_cols):
        return []
    
    # Get all SKUs that are BOM components (these should NOT be transferred)
    bom_component_skus = set()
    if bom_df is not None and 'Component SKU' in bom_df.columns:
        bom_component_skus = set(bom_df['Component SKU'].astype(str).unique())
    
    # Set warehouse-specific locations
    if warehouse == 'NC':
        armory_location = 'NC - Armory'
        main_location = 'NC - Main'
        main_locations = ['NC - Main']
    else:  # CA
        armory_location = 'CA - Armory'
        main_location = 'CA - Main'
        main_locations = ['CA - Main']
    
    # Find items in Armory with >20 units that are NOT BOM components
    armory_data = availability_df[availability_df[location_col] == armory_location]
    
    for _, item in armory_data.iterrows():
        sku = str(item[sku_col])
        on_hand_armory = item[on_hand_col]
        
        # Business logic: Transfer if >20 in Armory AND not a BOM component AND <20 in Main
        if on_hand_armory > 20 and sku not in bom_component_skus:
            # Check Main inventory for this SKU
            main_inv = calculate_inventory_position(availability_df, sku, main_locations)
            
            if main_inv['on_hand'] < 20:
                transfer_qty = min(on_hand_armory - 20, 20 - main_inv['on_hand'])
                if transfer_qty > 0:
                    transfer_recommendations.append({
                        'sku': sku,
                        'product_name': item.get(product_name_col, '') if product_name_col else '',
                        'from_location': armory_location,
                        'to_location': main_location,
                        'available_armory': on_hand_armory,
                        'current_main': main_inv['on_hand'],
                        'recommended_transfer': transfer_qty,
                        'reason': 'Balance inventory (not needed for assemblies)'
                    })
    
    return transfer_recommendations

def calculate_abc_analysis(profit_df):
    """Calculate ABC analysis based on cumulative profit (70-20-10 split)"""
    
    if profit_df is None or len(profit_df) == 0:
        return pd.DataFrame()
    
    # Get the first column as SKU column
    sku_col = profit_df.columns[0]
    
    # Get profit columns (exclude SKU column)
    profit_columns = [col for col in profit_df.columns if col != sku_col]
    
    # Calculate total profit for each SKU
    profit_df_copy = profit_df.copy()
    profit_df_copy['total_profit'] = profit_df_copy[profit_columns].sum(axis=1, skipna=True)
    
    # Sort by total profit descending
    profit_df_copy = profit_df_copy.sort_values('total_profit', ascending=False)
    
    # Calculate cumulative profit
    profit_df_copy['cumulative_profit'] = profit_df_copy['total_profit'].cumsum()
    total_profit = profit_df_copy['total_profit'].sum()
    profit_df_copy['cumulative_percentage'] = profit_df_copy['cumulative_profit'] / total_profit
    
    # Assign ABC categories
    profit_df_copy['abc_category'] = 'C'  # Default to C
    profit_df_copy.loc[profit_df_copy['cumulative_percentage'] <= 0.70, 'abc_category'] = 'A'
    profit_df_copy.loc[(profit_df_copy['cumulative_percentage'] > 0.70) & 
                       (profit_df_copy['cumulative_percentage'] <= 0.90), 'abc_category'] = 'B'
    
    # Return simplified result
    result = profit_df_copy[[sku_col, 'total_profit', 'abc_category']].copy()
    result.columns = ['SKU', 'total_profit', 'abc_category']
    result['SKU'] = result['SKU'].astype(str)
    
    return result

def run_assembly_order_generation():
    """Main function for Assembly Order Generation processing"""
    
    st.header("Assembly Order Generation")
    
    # Check if required dataframes are available
    required_dfs = ['BOM Report', 'Availability Report', 'Inventory List']
    sales_dfs = [df for df in st.session_state.dataframes.keys() if df.startswith('By Products -')]
    
    # Validation section
    with st.expander("📋 Data Validation", expanded=False):
        missing_files = []
        for df in required_dfs:
            if df in st.session_state.dataframes:
                st.write(f"✅ {df}")
            else:
                st.write(f"❌ {df}")
                missing_files.append(df)
        
        if sales_dfs:
            st.write(f"✅ By Products Data ({len(sales_dfs)} datasets available)")
        else:
            st.write("❌ By Products Data")
            missing_files.append("By Products Data")
    
    # Determine missing files for processing validation
    missing_files = []
    for df in required_dfs:
        if df not in st.session_state.dataframes:
            missing_files.append(df)
    
    if not sales_dfs:
        missing_files.append("By Products Data")
    
    # Processing button
    if missing_files:
        st.warning(f"⚠️ Missing required data files: {', '.join(missing_files)}")
        st.write("Please upload the missing files in the Upload Database tab before proceeding.")
        processing_enabled = False
    else:
        st.success("✅ All required data loaded successfully!")
        processing_enabled = True
    
    # Processing button
    st.subheader("🚀 Start Processing")
    
    # Warehouse selection
    col1, col2 = st.columns(2)
    with col1:
        warehouse = st.selectbox(
            "Select Warehouse:",
            ["All", "NC", "CA"],
            index=0,  # Default to "All"
            help="Choose which warehouse to generate assembly orders for. 'All' processes both NC and CA."
        )
    
    # Initialize session state for analysis results
    if 'assembly_analysis_results_nc' not in st.session_state:
        st.session_state.assembly_analysis_results_nc = None
    if 'assembly_analysis_results_ca' not in st.session_state:
        st.session_state.assembly_analysis_results_ca = None
    if 'transfer_recommendations_nc' not in st.session_state:
        st.session_state.transfer_recommendations_nc = None
    if 'transfer_recommendations_ca' not in st.session_state:
        st.session_state.transfer_recommendations_ca = None
    if 'replenish_df_nc' not in st.session_state:
        st.session_state.replenish_df_nc = None
    if 'replenish_df_ca' not in st.session_state:
        st.session_state.replenish_df_ca = None
    if 'sales_velocity_df' not in st.session_state:
        st.session_state.sales_velocity_df = None
    if 'abc_analysis' not in st.session_state:
        st.session_state.abc_analysis = None

    if st.button("Generate Assembly Orders", disabled=not processing_enabled, type="primary"):
        if processing_enabled:
            with st.spinner("Processing assembly orders..."):
                try:
                    # Get dataframes
                    bom_df = st.session_state.dataframes['BOM Report']
                    availability_df = st.session_state.dataframes['Availability Report'] 
                    inventory_df = st.session_state.dataframes['Inventory List']
                    
                    # Get sales data (prefer Quantity data)
                    quantity_df_name = None
                    for df_name in sales_dfs:
                        if 'Quantity' in df_name:
                            quantity_df_name = df_name
                            break
                    
                    if quantity_df_name:
                        sales_df = st.session_state.dataframes[quantity_df_name]
                        # st.success(f"✅ Using {quantity_df_name} for sales velocity calculation (UNITS)")
                    else:
                        # Fallback logic - but warn strongly
                        if sales_dfs:
                            sales_df = st.session_state.dataframes[sales_dfs[0]]
                            st.error(f"❌ Quantity data not found! Using {sales_dfs[0]} instead. This will likely produce incorrect results as it uses dollar amounts, not units.")
                            st.write("**Expected:** 'By Products - Quantity' dataframe")
                            st.write("**Found:** ", sales_dfs)
                        else:
                            st.error("❌ No By Products data found at all!")
                            return
                    
                    # Run the analysis pipeline (processing only, no display)
                    
                    # Step 1: Calculate sales velocity (shared between warehouses)
                    sales_velocity_df = calculate_sales_velocity(sales_df)
                    st.session_state.sales_velocity_df = sales_velocity_df
                    
                    # Step 2: ABC Analysis (shared between warehouses)
                    # Get profit data for ABC analysis
                    profit_df = None
                    for df_name in sales_dfs:
                        if 'Profit' in df_name:
                            profit_df = st.session_state.dataframes[df_name]
                            break
                    
                    if profit_df is not None:
                        abc_analysis = calculate_abc_analysis(profit_df)
                        st.session_state.abc_analysis = abc_analysis
                    else:
                        st.session_state.abc_analysis = pd.DataFrame()
                    
                    # Determine which warehouses to process
                    warehouses_to_process = ['NC', 'CA'] if warehouse == 'All' else [warehouse]
                    
                    for wh in warehouses_to_process:
                        # Step 3: Replenishment analysis
                        replenish_df = get_replenish_skus(bom_df, inventory_df, availability_df, sales_velocity_df, wh)
                        if wh == 'NC':
                            st.session_state.replenish_df_nc = replenish_df
                        else:
                            st.session_state.replenish_df_ca = replenish_df
                        
                        # Step 4: Assembly feasibility analysis
                        assembly_analysis = analyze_assembly_status(bom_df, availability_df, replenish_df, wh)
                        if wh == 'NC':
                            st.session_state.assembly_analysis_results_nc = assembly_analysis
                        else:
                            st.session_state.assembly_analysis_results_ca = assembly_analysis
                        
                        # Step 5: Transfer recommendations
                        transfer_recommendations = generate_transfer_recommendations(availability_df, bom_df, wh)
                        if wh == 'NC':
                            st.session_state.transfer_recommendations_nc = transfer_recommendations
                        else:
                            st.session_state.transfer_recommendations_ca = transfer_recommendations
                    
                    if warehouse == 'All':
                        st.success("✅ Assembly order generation completed for both NC and CA warehouses!")
                    else:
                        st.success(f"✅ {warehouse} Assembly order generation completed!")
                    
                except Exception as e:
                    st.error(f"Error during processing: {str(e)}")
                    st.exception(e)
        else:
            st.error("Cannot process: Missing required data files")
    
    # Display results sections for both warehouses
    st.subheader("📋 Generated Reports")
    
    # Tabs for NC and CA
    nc_tab, ca_tab = st.tabs(["🏭 North Carolina (NC)", "🌴 California (CA)"])
    
    with nc_tab:
        if st.session_state.assembly_analysis_results_nc is not None:
            assembly_analysis = st.session_state.assembly_analysis_results_nc
            
            if len(assembly_analysis) > 0:
                # NC Assembly Feasibility Analysis (first)
                display_warehouse_feasibility("NC", assembly_analysis, "nc")
                
                st.subheader("📋 NC Assembly Reports")
                
                # Report selection dropdown with optimized rendering
                report_type = st.selectbox(
                    "Select NC Report to View:",
                    [
                        "Assembly Orders (Ready for Production)", 
                        "Cannot Assemble Report", 
                        "Transfer Recommendations"
                    ],
                    index=0,
                    key="nc_assembly_report_type"
                )
                
                # NC Reports display logic
                display_warehouse_reports(assembly_analysis, st.session_state.transfer_recommendations_nc, "nc")
            else:
                st.info("No NC assembly data available. Please generate NC assembly orders first.")
        else:
            st.info("No NC assembly data available. Please generate NC assembly orders first.")
    
    with ca_tab:
        if st.session_state.assembly_analysis_results_ca is not None:
            assembly_analysis = st.session_state.assembly_analysis_results_ca
            
            if len(assembly_analysis) > 0:
                # CA Assembly Feasibility Analysis (first)
                display_warehouse_feasibility("CA", assembly_analysis, "ca")
                
                st.subheader("📋 CA Assembly Reports")
                
                # Report selection dropdown with optimized rendering
                report_type = st.selectbox(
                    "Select CA Report to View:",
                    [
                        "Assembly Orders (Ready for Production)", 
                        "Cannot Assemble Report", 
                        "Transfer Recommendations"
                    ],
                    index=0,
                    key="ca_assembly_report_type"
                )
                
                # CA Reports display logic
                display_warehouse_reports(assembly_analysis, st.session_state.transfer_recommendations_ca, "ca")
            else:
                st.info("No CA assembly data available. Please generate CA assembly orders first.")
        else:
            st.info("No CA assembly data available. Please generate CA assembly orders first.")

def display_warehouse_feasibility(warehouse_name, assembly_analysis, warehouse_key):
    """Display warehouse-specific assembly feasibility analysis"""
    
    # Assembly Feasibility Analysis (no title, just the expander)
    with st.expander(f"🔧 {warehouse_name} Assembly Feasibility Analysis", expanded=True):
        if len(assembly_analysis) == 0:
            st.info(f"No assemblies requiring replenishment found for {warehouse_name} based on current inventory levels and sales velocity.")
        else:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            ready_assemblies = [a for a in assembly_analysis if a['assembly_status'] == 'Ready for Production']
            cannot_assemble = [a for a in assembly_analysis if a['assembly_status'] == 'Cannot Assemble']
            
            with col1:
                st.metric(f"{warehouse_name} Total Assemblies", len(assembly_analysis))
            with col2:
                st.metric(f"{warehouse_name} Ready for Production", len(ready_assemblies))
            with col3:
                st.metric(f"{warehouse_name} Cannot Assemble", len(cannot_assemble))
            with col4:
                total_qty = sum([a['qty_for_assembly'] for a in ready_assemblies])
                st.metric(f"{warehouse_name} Total Units Ready", total_qty)

def display_warehouse_reports(assembly_analysis, transfer_recommendations, warehouse_key):
    """Display warehouse-specific reports"""
    
    # Get the report type from the appropriate selectbox
    if warehouse_key == "nc":
        report_type = st.session_state.get("nc_assembly_report_type", "Assembly Orders (Ready for Production)")
    else:
        report_type = st.session_state.get("ca_assembly_report_type", "Assembly Orders (Ready for Production)")
    
    # Pre-compute all reports once and cache them in session state to prevent reloading
    cache_key = f"{warehouse_key}_report_cache"
    if cache_key not in st.session_state:
        with st.spinner(f"Preparing {warehouse_key.upper()} reports..."):
            # Prepare all report DataFrames at once
            ready_assemblies = [a for a in assembly_analysis if a['assembly_status'] == 'Ready for Production']
            cannot_assemble = [a for a in assembly_analysis if a['assembly_status'] == 'Cannot Assemble']
            
            # Cache assembly orders DataFrame
            assembly_df = pd.DataFrame()
            if ready_assemblies:
                assembly_df = pd.DataFrame([{
                    'SKU': a['assembly_sku'],
                    'Assembly Name': a['assembly_name'],
                    'Quantity for Assembly': a['qty_for_assembly'],
                    'Available in Warehouse': a['available_in_warehouse'],
                    'Avg Monthly Sales': round(a['avg_monthly_sales'], 1)
                } for a in ready_assemblies]).sort_values('Quantity for Assembly', ascending=False)
            
            # Cache cannot assemble DataFrame
            cannot_assemble_df = pd.DataFrame()
            if cannot_assemble:
                cannot_assemble_df = pd.DataFrame([{
                    'SKU': a['assembly_sku'],
                    'Assembly Name': a['assembly_name'],
                    'Quantity Needed': a['qty_for_assembly'],
                    'Available in Warehouse': a['available_in_warehouse'],
                    'Avg Monthly Sales': round(a['avg_monthly_sales'], 1),
                    'Components Ready': f"{a['ready_components']}/{a['total_components']}",
                    'Missing Components': len([c for c in a['components'] if c['status'] == 'Shortage']),
                    'component_shortages': [c for c in a['components'] if c['status'] == 'Shortage']
                } for a in cannot_assemble])
            
            # Cache transfer DataFrame
            transfer_df = pd.DataFrame()
            if transfer_recommendations and len(transfer_recommendations) > 0:
                transfer_df = pd.DataFrame(transfer_recommendations)
            
            # Store all cached reports
            st.session_state[cache_key] = {
                'assembly_orders': assembly_df,
                'cannot_assemble': cannot_assemble_df,
                'transfer_recommendations': transfer_df,
                'ready_assemblies': ready_assemblies,
                'cannot_assemble_raw': cannot_assemble
            }
    
    # Get cached reports
    cached_reports = st.session_state[cache_key]
    
    # Display selected report without recomputation
    if report_type == "Assembly Orders (Ready for Production)":
        assembly_df = cached_reports['assembly_orders']
        
        if len(assembly_df) == 0:
            st.info("No assemblies are currently ready for production.")
        else:
            st.subheader("🏭 Assembly Orders - Ready for Production")
            st.write(f"**{len(assembly_df)} assemblies ready for production**")
            st.dataframe(assembly_df, use_container_width=True, height=400)
            
            # Download button
            csv = convert_assembly_to_csv(assembly_df, f"{warehouse_key}_ready_download")
            st.download_button(
                label="📥 Download Assembly Orders CSV",
                data=csv,
                file_name=f"assembly_orders_ready_for_production_{warehouse_key}.csv",
                mime='text/csv',
                key=f"download_assembly_orders_{warehouse_key}"
            )
    
    elif report_type == "Cannot Assemble Report":
        cannot_assemble_df = cached_reports['cannot_assemble']
        cannot_assemble_raw = cached_reports['cannot_assemble_raw']
        
        if len(cannot_assemble_df) == 0:
            st.info("All assemblies are ready for production - no component shortages found.")
        else:
            st.subheader("❌ Cannot Assemble Report")
            st.write(f"**{len(cannot_assemble_df)} assemblies cannot be completed due to component shortages**")
            
            # Display main table (without component_shortages column)
            display_df = cannot_assemble_df.drop(columns=['component_shortages'], errors='ignore')
            st.dataframe(display_df, use_container_width=True, height=400)
            
            # Component shortage details
            if not cannot_assemble_df.empty:
                st.subheader("🔍 Component Shortage Details")
                selected_cannot_assemble = st.selectbox(
                    "Select assembly to view component shortages:", 
                    cannot_assemble_df['SKU'].tolist(),
                    key=f"selected_cannot_assemble_detail_{warehouse_key}"
                )
                
                if selected_cannot_assemble:
                    selected_row = cannot_assemble_df[cannot_assemble_df['SKU'] == selected_cannot_assemble]
                    if not selected_row.empty and 'component_shortages' in selected_row.columns:
                        shortage_components = selected_row['component_shortages'].iloc[0]
                        if shortage_components:
                            shortage_df = create_shortage_df(shortage_components, f"{warehouse_key}_shortage")
                            # Remove duplicates based on Component SKU
                            shortage_df = shortage_df.drop_duplicates(subset=['Component SKU'], keep='first')
                            st.dataframe(shortage_df, use_container_width=True)
            
            # Download button
            csv = convert_cannot_assemble_to_csv(display_df, f"{warehouse_key}_cannot_download")
            st.download_button(
                label="📥 Download Cannot Assemble Report CSV",
                data=csv,
                file_name=f"cannot_assemble_report_{warehouse_key}.csv",
                mime='text/csv',
                key=f"download_cannot_assemble_{warehouse_key}"
            )
    
    elif report_type == "Transfer Recommendations":
        transfer_df = cached_reports['transfer_recommendations']
        
        if len(transfer_df) == 0:
            st.info("No transfer recommendations generated.")
        else:
            st.subheader("🚚 Transfer Recommendations")
            st.write(f"**{len(transfer_df)} transfer recommendations to balance inventory**")
            st.dataframe(transfer_df, use_container_width=True, height=400)
            
            # Download button
            csv = convert_transfer_to_csv(transfer_df, f"{warehouse_key}_transfer_download")
            st.download_button(
                label="📥 Download Transfer Recommendations CSV",
                data=csv,
                file_name=f"transfer_recommendations_{warehouse_key}.csv",
                mime='text/csv',
                key=f"download_transfer_{warehouse_key}"
            )
    
    # Detailed component analysis section (available for all reports)
    if report_type in ["Assembly Orders (Ready for Production)", "Cannot Assemble Report"]:
        st.divider()
        st.subheader("🔧 Detailed Component Analysis")
        
        assembly_skus = [a['assembly_sku'] for a in assembly_analysis]
        if assembly_skus:
            selected_assembly = st.selectbox("Select assembly for detailed component analysis:", assembly_skus, key=f"detailed_selected_assembly_{warehouse_key}")
            
            if selected_assembly:
                selected_data = next(a for a in assembly_analysis if a['assembly_sku'] == selected_assembly)
                
                st.write(f"**Assembly:** {selected_data['assembly_name']} ({selected_assembly})")
                st.write(f"**Quantity Needed:** {selected_data['qty_for_assembly']}")
                st.write(f"**Status:** {selected_data['assembly_status']}")
                st.write(f"**Warehouse:** {selected_data['warehouse']}")
                
                # Component details table - remove duplicates
                component_df = pd.DataFrame([{
                    'Component SKU': c['component_sku'],
                    'Component Name': c['component_name'],
                    'Qty per Assembly': c['qty_per_assembly'],
                    'Total Needed': c['total_needed'],
                    'Available': c['available'],
                    'Shortage': c['shortage'],
                    'Status': c['status']
                } for c in selected_data['components']])
                
                # Remove duplicates based on Component SKU
                component_df = component_df.drop_duplicates(subset=['Component SKU'], keep='first')
                
                st.dataframe(component_df, use_container_width=True)

# Additional cached functions for optimized performance
@st.cache_data
def create_assembly_df(assemblies_data, cache_key):
    """Create assembly DataFrame with caching"""
    return pd.DataFrame([{
        'SKU': a['assembly_sku'],
        'Assembly Name': a['assembly_name'],
        'Quantity for Assembly': a['qty_for_assembly'],
        'Available in Warehouse': a['available_in_warehouse'],
        'Avg Monthly Sales': round(a['avg_monthly_sales'], 1)
    } for a in assemblies_data]).sort_values('Quantity for Assembly', ascending=False)

@st.cache_data  
def convert_assembly_to_csv(dataframe, cache_key):
    """Convert assembly DataFrame to CSV with caching"""
    return dataframe.to_csv(index=False)

@st.cache_data
def create_cannot_assemble_df(assemblies_data, cache_key):
    """Create cannot assemble DataFrame with caching"""
    return pd.DataFrame([{
        'SKU': a['assembly_sku'],
        'Assembly Name': a['assembly_name'],
        'Quantity Needed': a['qty_for_assembly'],
        'Available in Warehouse': a['available_in_warehouse'],
        'Avg Monthly Sales': round(a['avg_monthly_sales'], 1),
        'Components Ready': f"{a['ready_components']}/{a['total_components']}",
        'Missing Components': len([c for c in a['components'] if c['status'] == 'Shortage']),
        'component_shortages': [c for c in a['components'] if c['status'] == 'Shortage']
    } for a in assemblies_data])

@st.cache_data
def convert_cannot_assemble_to_csv(dataframe, cache_key):
    """Convert cannot assemble DataFrame to CSV with caching"""
    # Remove the component_shortages column for CSV export
    export_df = dataframe.drop(columns=['component_shortages'], errors='ignore')
    return export_df.to_csv(index=False)

@st.cache_data
def create_shortage_df(components_data, cache_key):
    """Create component shortage DataFrame with caching"""
    return pd.DataFrame([{
        'Component SKU': c['component_sku'],
        'Component Name': c['component_name'],
        'Needed': c['total_needed'],
        'Available': c['available'],
        'Shortage': c['shortage']
    } for c in components_data])

@st.cache_data
def create_transfer_df(transfer_data, cache_key):
    """Create transfer DataFrame with caching"""
    return pd.DataFrame(transfer_data)

@st.cache_data
def convert_transfer_to_csv(dataframe, cache_key):
    """Convert transfer DataFrame to CSV with caching"""
    return dataframe.to_csv(index=False)
