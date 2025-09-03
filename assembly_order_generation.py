import streamlit as st
import pandas as pd
import numpy as np

def calculate_sales_velocity(sales_df):
    """Calculate average daily sales from 6 months of data"""
    if sales_df is None or len(sales_df) == 0:
        return pd.DataFrame(columns=['SKU', 'avg_daily_sales', 'avg_monthly_sales'])
    
    # Debug: Show what data we're working with
    st.write(f"**Sales velocity calculation input:**")
    st.write(f"- DataFrame shape: {sales_df.shape}")
    st.write(f"- Columns: {list(sales_df.columns)}")
    
    # Get the first column as SKU column
    sku_col = sales_df.columns[0]
    
    # Get sales columns (exclude SKU column and Total/Average columns)
    sales_columns = [col for col in sales_df.columns if col != sku_col and not col.startswith('Total') and not col.startswith('Average')]
    st.write(f"- Using columns for calculation: {sales_columns}")
    
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

def get_replenish_skus(bom_df, inventory_df, availability_df, sales_velocity_df):
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
        
        # Get inventory position
        inv_position = calculate_inventory_position(availability_df, sku)
        
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
        available_in_nc = inv_position['total_available']
        needs_replenishment = (available_in_nc + inv_position['on_order']) < avg_monthly_sales
        
        if needs_replenishment and replenishment_qty > 0:
            # Calculate quantity for assembly with reasonable bounds
            base_qty = max(2, round(avg_monthly_sales - available_in_nc))
            
            # Apply reasonable limits based on monthly sales velocity
            # Cap at 3x monthly sales to prevent unrealistic quantities
            max_reasonable_qty = max(10, round(avg_monthly_sales * 3))
            
            # Also consider a hard cap for very high-velocity items
            absolute_max = 1000  # No single assembly order should exceed 1000 units
            
            qty_for_assembly = min(base_qty, max_reasonable_qty, absolute_max)
            
            replenish_list.append({
                'SKU': str(sku),  # Ensure SKU is stored as string
                'avg_daily_sales': avg_daily_sales,
                'avg_monthly_sales': avg_monthly_sales,
                'available_in_nc': available_in_nc,
                'on_order': inv_position['on_order'],
                'target_inventory': target_inventory,
                'qty_for_assembly': qty_for_assembly
            })
    
    return pd.DataFrame(replenish_list)

def analyze_assembly_status(bom_df, availability_df, replenish_df):
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
            
            # Get component inventory in NC locations
            component_inv = calculate_inventory_position(availability_df, component_sku)
            
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
            'available_in_nc': replenish_row['available_in_nc'],
            'components': component_analysis,
            'total_components': len(component_analysis),
            'ready_components': len([c for c in component_analysis if c['status'] == 'Ready'])
        })
    
    return assembly_analysis

def generate_transfer_recommendations(availability_df, bom_df):
    """Generate recommendations for transfers from NC-Armory to NC-Main based on business logic"""
    
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
    
    # Find items in NC-Armory with >20 units that are NOT BOM components
    armory_data = availability_df[availability_df[location_col] == 'NC - Armory']
    
    for _, item in armory_data.iterrows():
        sku = str(item[sku_col])
        on_hand_armory = item[on_hand_col]
        
        # Business logic: Transfer if >20 in Armory AND not a BOM component AND <20 in Main
        if on_hand_armory > 20 and sku not in bom_component_skus:
            # Check NC-Main inventory for this SKU
            main_inv = calculate_inventory_position(availability_df, sku, ['NC - Main'])
            
            if main_inv['on_hand'] < 20:
                transfer_qty = min(on_hand_armory - 20, 20 - main_inv['on_hand'])
                if transfer_qty > 0:
                    transfer_recommendations.append({
                        'sku': sku,
                        'product_name': item.get(product_name_col, '') if product_name_col else '',
                        'from_location': 'NC - Armory',
                        'to_location': 'NC - Main',
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
    st.subheader("📋 Data Validation")
    
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
    
    # Initialize session state for analysis results
    if 'assembly_analysis_results' not in st.session_state:
        st.session_state.assembly_analysis_results = None
    if 'transfer_recommendations' not in st.session_state:
        st.session_state.transfer_recommendations = None
    if 'replenish_df' not in st.session_state:
        st.session_state.replenish_df = None
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
                    st.write("**Available By Products data:**", sales_dfs)
                    
                    # Look specifically for Quantity data
                    quantity_df_name = None
                    for df_name in sales_dfs:
                        if 'Quantity' in df_name:
                            quantity_df_name = df_name
                            break
                    
                    if quantity_df_name:
                        sales_df = st.session_state.dataframes[quantity_df_name]
                        st.success(f"✅ Using {quantity_df_name} for sales velocity calculation (UNITS)")
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
                    
                    # Run the analysis pipeline
                    st.subheader("📊 Analysis Results")
                    
                    # Step 1: Calculate sales velocity
                    with st.expander("🔄 Step 1: Sales Velocity Calculation", expanded=False):
                        sales_velocity_df = calculate_sales_velocity(sales_df)
                        st.session_state.sales_velocity_df = sales_velocity_df
                        st.write(f"Calculated sales velocity for {len(sales_velocity_df)} SKUs")
                        st.dataframe(sales_velocity_df.head(), use_container_width=True)
                    
                    # Step 2: Identify replenishment needs
                    with st.expander("📈 Step 2: Replenishment Analysis", expanded=False):
                        replenish_df = get_replenish_skus(bom_df, inventory_df, availability_df, sales_velocity_df)
                        st.session_state.replenish_df = replenish_df
                        st.write(f"**Found {len(replenish_df)} SKUs requiring replenishment**")
                        if len(replenish_df) > 0:
                            st.dataframe(replenish_df, use_container_width=True)
                    
                    # Step 3: Assembly feasibility analysis
                    with st.expander("🔧 Step 3: Assembly Feasibility Analysis", expanded=True):
                        assembly_analysis = analyze_assembly_status(bom_df, availability_df, replenish_df)
                        st.session_state.assembly_analysis_results = assembly_analysis
                        
                        if len(assembly_analysis) == 0:
                            st.info("No assemblies requiring replenishment found based on current inventory levels and sales velocity.")
                        else:
                            # Summary metrics
                            col1, col2, col3, col4 = st.columns(4)
                            
                            ready_assemblies = [a for a in assembly_analysis if a['assembly_status'] == 'Ready for Production']
                            cannot_assemble = [a for a in assembly_analysis if a['assembly_status'] == 'Cannot Assemble']
                            
                            with col1:
                                st.metric("Total Assemblies", len(assembly_analysis))
                            with col2:
                                st.metric("Ready for Production", len(ready_assemblies))
                            with col3:
                                st.metric("Cannot Assemble", len(cannot_assemble))
                            with col4:
                                total_qty = sum([a['qty_for_assembly'] for a in ready_assemblies])
                                st.metric("Total Units Ready", total_qty)
                    
                    # Step 4: ABC Analysis
                    with st.expander("📊 Step 4: ABC Analysis", expanded=False):
                        # Get profit data for ABC analysis
                        profit_df = None
                        for df_name in sales_dfs:
                            if 'Profit' in df_name:
                                profit_df = st.session_state.dataframes[df_name]
                                break
                        
                        if profit_df is not None:
                            abc_analysis = calculate_abc_analysis(profit_df)
                            st.session_state.abc_analysis = abc_analysis
                            st.write(f"ABC Analysis completed for {len(abc_analysis)} SKUs")
                            
                            # Show ABC distribution
                            abc_counts = abc_analysis['abc_category'].value_counts()
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Category A (70%)", abc_counts.get('A', 0))
                            with col2:
                                st.metric("Category B (20%)", abc_counts.get('B', 0))
                            with col3:
                                st.metric("Category C (10%)", abc_counts.get('C', 0))
                        else:
                            st.warning("Profit data not available for ABC analysis")
                            st.session_state.abc_analysis = pd.DataFrame()
                    
                    # Step 5: Transfer recommendations
                    with st.expander("🚚 Step 5: Transfer Recommendations", expanded=False):
                        transfer_recommendations = generate_transfer_recommendations(availability_df, bom_df)
                        st.session_state.transfer_recommendations = transfer_recommendations
                        
                        if len(transfer_recommendations) > 0:
                            st.write(f"Generated {len(transfer_recommendations)} transfer recommendations")
                            transfer_df = pd.DataFrame(transfer_recommendations)
                            st.dataframe(transfer_df, use_container_width=True)
                        else:
                            st.info("No transfer recommendations generated")
                    
                    st.success("✅ Assembly order generation completed!")
                    
                except Exception as e:
                    st.error(f"Error during processing: {str(e)}")
                    st.exception(e)
        else:
            st.error("Cannot process: Missing required data files")
    
    # Display results if they exist in session state
    if st.session_state.assembly_analysis_results is not None:
        assembly_analysis = st.session_state.assembly_analysis_results
        
        if len(assembly_analysis) > 0:
            st.subheader("📋 Generated Reports")
            
            # Report selection dropdown with optimized rendering
            report_type = st.selectbox(
                "Select Report to View:",
                [
                    "Assembly Orders (Ready for Production)", 
                    "Cannot Assemble Report", 
                    "Transfer Recommendations"
                ],
                index=0,
                key="assembly_report_type"
            )
            
            # Use containers to optimize rendering and prevent unnecessary reruns
            if report_type == "Assembly Orders (Ready for Production)":
                with st.container():
                    # Assembly Orders Report
                    ready_assemblies = [a for a in assembly_analysis if a['assembly_status'] == 'Ready for Production']
                    
                    if ready_assemblies:
                        st.subheader("🏭 Assembly Orders - Ready for Production")
                        st.write(f"**{len(ready_assemblies)} assemblies ready for production**")
                        
                        # Cache the dataframe creation to avoid recreation on each rerun
                        @st.cache_data
                        def create_assembly_df(assemblies_data):
                            return pd.DataFrame([{
                                'SKU': a['assembly_sku'],
                                'Assembly Name': a['assembly_name'],
                                'Quantity for Assembly': a['qty_for_assembly'],
                                'Available in NC': a['available_in_nc'],
                                'Avg Monthly Sales': round(a['avg_monthly_sales'], 1),
                                'Components Ready': f"{a['ready_components']}/{a['total_components']}"
                            } for a in assemblies_data]).sort_values('Quantity for Assembly', ascending=False)
                        
                        assembly_df = create_assembly_df(ready_assemblies)
                        st.dataframe(assembly_df, use_container_width=True, height=400)
                        
                        # Download option with cached CSV generation
                        @st.cache_data
                        def convert_assembly_to_csv(dataframe):
                            return dataframe.to_csv(index=False)
                        
                        csv = convert_assembly_to_csv(assembly_df)
                        st.download_button(
                            label="📥 Download Assembly Orders CSV",
                            data=csv,
                            file_name="assembly_orders_ready_for_production.csv",
                            mime='text/csv'
                        )
                    else:
                        st.info("No assemblies are currently ready for production.")
            
            elif report_type == "Cannot Assemble Report":
                with st.container():
                    # Cannot Assemble Report
                    cannot_assemble = [a for a in assembly_analysis if a['assembly_status'] == 'Cannot Assemble']
                    
                    if cannot_assemble:
                        st.subheader("❌ Cannot Assemble Report")
                        st.write(f"**{len(cannot_assemble)} assemblies cannot be completed due to component shortages**")
                        
                        # Cache the dataframe creation
                        @st.cache_data
                        def create_cannot_assemble_df(assemblies_data):
                            return pd.DataFrame([{
                                'SKU': a['assembly_sku'],
                                'Assembly Name': a['assembly_name'],
                                'Quantity Needed': a['qty_for_assembly'],
                                'Available in NC': a['available_in_nc'],
                                'Avg Monthly Sales': round(a['avg_monthly_sales'], 1),
                                'Components Ready': f"{a['ready_components']}/{a['total_components']}",
                                'Missing Components': len([c for c in a['components'] if c['status'] == 'Shortage'])
                            } for a in assemblies_data])
                        
                        cannot_assemble_df = create_cannot_assemble_df(cannot_assemble)
                        st.dataframe(cannot_assemble_df, use_container_width=True, height=400)
                        
                        # Component shortage details
                        st.subheader("🔍 Component Shortage Details")
                        selected_cannot_assemble = st.selectbox(
                            "Select assembly to view component shortages:", 
                            [a['assembly_sku'] for a in cannot_assemble],
                            key="selected_cannot_assemble_detail"
                        )
                        
                        if selected_cannot_assemble:
                            selected_data = next(a for a in cannot_assemble if a['assembly_sku'] == selected_cannot_assemble)
                            
                            shortage_components = [c for c in selected_data['components'] if c['status'] == 'Shortage']
                            if shortage_components:
                                @st.cache_data
                                def create_shortage_df(components_data):
                                    return pd.DataFrame([{
                                        'Component SKU': c['component_sku'],
                                        'Component Name': c['component_name'],
                                        'Needed': c['total_needed'],
                                        'Available': c['available'],
                                        'Shortage': c['shortage']
                                    } for c in components_data])
                                
                                shortage_df = create_shortage_df(shortage_components)
                                st.dataframe(shortage_df, use_container_width=True)
                        
                        # Download option with cached CSV
                        @st.cache_data
                        def convert_cannot_assemble_to_csv(dataframe):
                            return dataframe.to_csv(index=False)
                        
                        csv = convert_cannot_assemble_to_csv(cannot_assemble_df)
                        st.download_button(
                            label="📥 Download Cannot Assemble Report CSV",
                            data=csv,
                            file_name="cannot_assemble_report.csv",
                            mime='text/csv'
                        )
                    else:
                        st.info("All assemblies are ready for production - no component shortages found.")
            
            elif report_type == "Transfer Recommendations":
                with st.container():
                    # Transfer Recommendations Report
                    if hasattr(st.session_state, 'transfer_recommendations') and st.session_state.transfer_recommendations:
                        st.subheader("🚚 Transfer Recommendations")
                        
                        # Cache the dataframe creation
                        @st.cache_data
                        def create_transfer_df(transfer_data):
                            return pd.DataFrame(transfer_data)
                        
                        transfer_df = create_transfer_df(st.session_state.transfer_recommendations)
                        
                        st.write(f"**{len(transfer_df)} transfer recommendations to balance inventory**")
                        st.dataframe(transfer_df, use_container_width=True, height=400)
                        
                        # Download option with cached CSV
                        @st.cache_data
                        def convert_transfer_to_csv(dataframe):
                            return dataframe.to_csv(index=False)
                        
                        csv = convert_transfer_to_csv(transfer_df)
                        st.download_button(
                            label="📥 Download Transfer Recommendations CSV",
                            data=csv,
                            file_name="transfer_recommendations.csv",
                            mime='text/csv'
                        )
                    else:
                        st.info("No transfer recommendations generated.")
            
            
            # Detailed component analysis section (available for all reports)
            if report_type in ["Assembly Orders (Ready for Production)", "Cannot Assemble Report"]:
                st.divider()
                st.subheader("🔧 Detailed Component Analysis")
                
                assembly_skus = [a['assembly_sku'] for a in assembly_analysis]
                if assembly_skus:
                    selected_assembly = st.selectbox("Select assembly for detailed component analysis:", assembly_skus, key="detailed_selected_assembly")
                    
                    if selected_assembly:
                        selected_data = next(a for a in assembly_analysis if a['assembly_sku'] == selected_assembly)
                        
                        st.write(f"**Assembly:** {selected_data['assembly_name']} ({selected_assembly})")
                        st.write(f"**Quantity Needed:** {selected_data['qty_for_assembly']}")
                        st.write(f"**Status:** {selected_data['assembly_status']}")
                        
                        # Component details table
                        component_df = pd.DataFrame([{
                            'Component SKU': c['component_sku'],
                            'Component Name': c['component_name'],
                            'Qty per Assembly': c['qty_per_assembly'],
                            'Total Needed': c['total_needed'],
                            'Available': c['available'],
                            'Shortage': c['shortage'],
                            'Status': c['status']
                        } for c in selected_data['components']])
                        
                        st.dataframe(component_df, use_container_width=True)
