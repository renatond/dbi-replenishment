import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import tempfile

def load_excluded_suppliers():
    """Loads the list of excluded suppliers from session state or creates default list."""
    if 'excluded_suppliers' not in st.session_state:
        # Default excluded suppliers list
        st.session_state.excluded_suppliers = [
            'devil dog concepts', 'apoc armory', 'tiger rock inc.', 'crow shooting supply', 'Havoc Tactical Solutions Llc', 
            'sellway armory', 'true shot gun club', 'andrew bergquist', 'in-store purchase', 'point 2 point global solutions', 
            'unknown', 'apparel.com', 'dbi, llc', 'dbi bakersfield customers', 'dbi bakersfield', 'midway usa', 'J&G Sales', 
            'Mellingers Brass Bees', 'FIN FEATHER FUR OUTFITTERS', 'sionics weapon systems', 'primary weapon systems', 
            'n.a.g. industries', 'modern armory', 'jlo metal products', 'War Dog Industries', 'r & j legacy inc.', 
            'Miwall Corp'
        ]
    return [supplier.lower() for supplier in st.session_state.excluded_suppliers]

def calculate_profit_margin(df):
    """Calculates the profit margin for each product."""
    # Profit Margin = Total Profit / Total Sales
    # Avoid division by zero
    df['ProfitMargin'] = df.apply(
        lambda row: row['TotalProfit'] / row['TotalSales'] if row['TotalSales'] != 0 else 0,
        axis=1
    )
    return df

def adjust_sales_velocity(df):
    """Adjusts sales velocity based on profit margin and price tier."""
    
    # Clean 'Cost price' column
    df['Cost price'] = pd.to_numeric(df['Cost price'], errors='coerce').fillna(0)

    def get_adjustment(row):
        margin = row['ProfitMargin']
        price = row['Cost price']
        
        # Tier 1: Under $100
        if price < 100:
            if margin < 0.1: return -0.8
            if 0.1 <= margin < 0.2: return -0.5
            if 0.2 <= margin < 0.25: return -0.2
            if 0.26 <= margin <= 0.33: return 0
            if margin > 0.33: return 0.1
        # Tier 2: $100–$250
        elif 100 <= price < 250:
            if margin < 0.1: return -0.8
            if 0.1 <= margin < 0.2: return -0.5
            if 0.2 <= margin <= 0.3: return 0
            if margin > 0.3: return 0.05
        # Tier 3: $250–$750
        elif 250 <= price < 750:
            if margin < 0.05: return -0.8
            if 0.05 <= margin < 0.15: return -0.5
            if 0.15 <= margin <= 0.28: return 0
            if margin > 0.28: return 0.03
        # Tier 4: $750+
        elif price >= 750:
            if margin < 0.05: return -0.9
            if 0.05 <= margin < 0.12: return -0.6
            if 0.12 <= margin <= 0.25: return 0
            if margin > 0.25: return 0.02
        return 0

    df['VelocityAdjustment'] = df.apply(get_adjustment, axis=1)
    df['AdjustedSalesVelocity'] = df['Adjusted sales velocity/day'] * (1 + df['VelocityAdjustment'])
    
    return df

def calculate_po_quantity(df):
    """Calculates the final purchase order quantity."""
    # Days of Stock = Lead Time + 3 days
    df['Lead time'] = pd.to_numeric(df['Lead time'], errors='coerce').fillna(0)
    df['DaysOfStock'] = df['Lead time'] + 3
    
    # Target stock level
    df['TargetStock'] = df['AdjustedSalesVelocity'] * df['DaysOfStock']
    
    # Ensure TotalStock and TotalOnOrder are numbers and fill missing with 0
    df['TotalStock'] = pd.to_numeric(df['TotalStock'], errors='coerce').fillna(0)
    df['TotalOnOrder'] = pd.to_numeric(df['TotalOnOrder'], errors='coerce').fillna(0)
    
    # PO Quantity = Target Stock - Current Stock - On Order Stock
    df['PO_Quantity'] = df['TargetStock'] - df['TotalStock'] - df['TotalOnOrder']
    
    # Don't order if we have enough stock
    df.loc[df['PO_Quantity'] < 0, 'PO_Quantity'] = 0

    # Round up to the nearest whole number
    df['PO_Quantity'] = df['PO_Quantity'].apply(lambda x: int(x) + 1 if x > int(x) else int(x))

    return df

def generate_po_csv(df, location):
    """Generates the final CSV for Cin7 Core import."""
    
    # Calculate Adjusted Monthly Sales before any aggregation
    df['Adjusted Monthly Sales'] = df['Adjusted sales velocity/day'] * 30
    
    # Select and prepare columns for the PO
    available_columns = ['LastSuppliedBy', 'SKU', 'PO_Quantity', 'Cost price', 'Lead time', 'Adjusted Monthly Sales']
    
    # Check if SupplierProductCode is available and add it after supplier
    if 'SupplierProductCode' in df.columns:
        available_columns.insert(1, 'SupplierProductCode')  # Insert after LastSuppliedBy
    
    # Check if ProductName is available and add it after SKU
    if 'ProductName' in df.columns:
        sku_index = available_columns.index('SKU')
        available_columns.insert(sku_index + 1, 'ProductName')  # Insert after SKU
    
    # Select only columns that exist in the dataframe
    existing_columns = [col for col in available_columns if col in df.columns]
    po_data = df[existing_columns].copy()
    
    # Rename core columns for Cin7 import
    rename_mapping = {
        'LastSuppliedBy': 'SupplierName*',
        'SKU': 'Product*', 
        'PO_Quantity': 'Quantity*',
        'Cost price': 'Price/Amount*'
    }
    po_data.rename(columns=rename_mapping, inplace=True)
    
    # Filter out rows with no supplier or zero quantity
    po_data = po_data[po_data['SupplierName*'].notna()]
    po_data = po_data[po_data['Quantity*'] > 0]
    
    # Filter out excluded suppliers (case-insensitive)
    excluded_suppliers = load_excluded_suppliers()
    if excluded_suppliers:
        original_count = len(po_data)
        po_data = po_data[~po_data['SupplierName*'].str.lower().isin(excluded_suppliers)]
        excluded_count = original_count - len(po_data)
        st.info(f"Filtered out {excluded_count} items from excluded suppliers.")

    # For aggregation, we need to group by columns that should be the same for each product+supplier
    group_cols = ['SupplierName*', 'Product*', 'Price/Amount*']
    agg_dict = {'Quantity*': 'sum'}
    
    # Add non-aggregated columns to the group (they should be the same for each product)
    preserve_cols = []
    for col in po_data.columns:
        if col not in group_cols and col != 'Quantity*':
            preserve_cols.append(col)
            agg_dict[col] = 'first'  # Take the first value since they should be the same
    
    # Aggregate quantities for the same product and supplier
    po_data = po_data.groupby(group_cols).agg(agg_dict).reset_index()

    # Add other required columns with default values
    po_data['RecordType*'] = 'Order'
    
    # Define the final column order
    final_columns = ['RecordType*', 'SupplierName*']
    
    # Add SupplierProductCode if it exists
    if 'SupplierProductCode' in po_data.columns:
        final_columns.append('SupplierProductCode')
    
    # Add the core required columns
    final_columns.append('Product*')
    
    # Add product name right after SKU if it exists  
    if 'ProductName' in po_data.columns:
        final_columns.append('ProductName')
    
    # Continue with remaining core columns
    final_columns.extend(['Quantity*', 'Price/Amount*'])
    
    # Add the additional informational columns at the end
    if 'Lead time' in po_data.columns:
        final_columns.append('Lead time')
    if 'Adjusted Monthly Sales' in po_data.columns:
        final_columns.append('Adjusted Monthly Sales')
    
    # Select only columns that exist in our data
    final_columns = [col for col in final_columns if col in po_data.columns]
    po_data = po_data[final_columns]

    return po_data

def run_po_generation(dataframes, location):
    """Main function to run the PO generation process for a specific location."""
    
    try:
        # Get sales data - prefer combined, fall back to separate
        sales_df = None
        cogs_df = None
        profit_df = None
        quantity_df = None
        
        # Check for combined sales data
        if 'By Products - Sale' in dataframes and 'By Products - COGS' in dataframes and 'By Products - Profit' in dataframes and 'By Products - Quantity' in dataframes:
            st.info("Using combined Sales by Product Details Report data...")
            
            # Get the individual metric dataframes and sum across months
            sales_df = dataframes['By Products - Sale'].copy()
            cogs_df = dataframes['By Products - COGS'].copy()
            profit_df = dataframes['By Products - Profit'].copy()
            quantity_df = dataframes['By Products - Quantity'].copy()
            
            # Sum sales across all month columns for each SKU
            sales_cols = [col for col in sales_df.columns if col != 'SKU']
            sales_df['TotalSales'] = sales_df[sales_cols].sum(axis=1, skipna=True)
            sales_df = sales_df[['SKU', 'TotalSales']]
            
            # Sum COGS across all month columns for each SKU
            cogs_cols = [col for col in cogs_df.columns if col != 'SKU']
            cogs_df['TotalCOGS'] = cogs_df[cogs_cols].sum(axis=1, skipna=True)
            cogs_df = cogs_df[['SKU', 'TotalCOGS']]
            
            # Sum profit across all month columns for each SKU
            profit_cols = [col for col in profit_df.columns if col != 'SKU']
            profit_df['TotalProfit'] = profit_df[profit_cols].sum(axis=1, skipna=True)
            profit_df = profit_df[['SKU', 'TotalProfit']]
            
            # Sum quantity across all month columns for each SKU
            quantity_cols = [col for col in quantity_df.columns if col != 'SKU']
            quantity_df['TotalQuantity'] = quantity_df[quantity_cols].sum(axis=1, skipna=True)
            quantity_df = quantity_df[['SKU', 'TotalQuantity']]
            
        else:
            st.error("Sales by Product Details Report data not found. Please upload the required sales data.")
            return None
        
        # Get replenishment data
        replenishment_df = None
        for df_name in dataframes.keys():
            if f'Replenishment Report - {location.upper()}' in df_name:
                replenishment_df = dataframes[df_name]
                break
        
        if replenishment_df is None:
            st.error(f"Replenishment Report for {location.upper()} not found. Please upload the required replenishment data.")
            return None
        
        # Get inventory and availability data
        inventory_df = dataframes.get('Inventory List')
        availability_df = dataframes.get('Availability Report')
        
        if inventory_df is None:
            st.error("Inventory List not found. Please upload the required inventory data.")
            return None
            
        if availability_df is None:
            st.error("Availability Report not found. Please upload the required availability data.")
            return None
        
        # Process availability data for the specific location
        location_availability = availability_df[availability_df['Location'].str.startswith(location.upper(), na=False)]
        agg_stock = location_availability.groupby('SKU').agg(
            TotalStock=('Available', 'sum'),
            TotalOnOrder=('OnOrder', 'sum')
        ).reset_index()
        
        # Merge sales data
        merged_sales = sales_df.merge(cogs_df, on="SKU", how="outer")
        merged_sales = merged_sales.merge(profit_df, on="SKU", how="outer")
        merged_sales = merged_sales.merge(quantity_df, on="SKU", how="outer")
        
        # Ensure SKU types are consistent for merging
        replenishment_df['SKU'] = replenishment_df['SKU'].astype(str)
        merged_sales['SKU'] = merged_sales['SKU'].astype(str)
        inventory_df['ProductCode'] = inventory_df['ProductCode'].astype(str)
        agg_stock['SKU'] = agg_stock['SKU'].astype(str)

        # Merge replenishment data with sales data
        df = replenishment_df.merge(merged_sales, on='SKU', how='left')

        # Merge with inventory data
        df = df.merge(inventory_df, left_on='SKU', right_on='ProductCode', how='left')

        # Handle Name column conflict (both replenishment and inventory have 'Name')
        # Use inventory Name (Name_y) as it's more authoritative, rename it back to 'Name'
        if 'Name_y' in df.columns:
            df['ProductName'] = df['Name_y']  # Use inventory product name
            df = df.drop(columns=['Name_x', 'Name_y'])  # Clean up duplicate name columns
        elif 'Name_x' in df.columns:
            df['ProductName'] = df['Name_x']  # Fallback to replenishment name
            df = df.drop(columns=['Name_x'])

        # Merge with availability data
        df = df.merge(agg_stock, on='SKU', how='left')
        
        # Calculate profit margin
        df = calculate_profit_margin(df)
        
        # Adjust sales velocity
        df = adjust_sales_velocity(df)

        # Calculate PO quantity
        df = calculate_po_quantity(df)
        
        # Generate PO CSV data
        po_data = generate_po_csv(df, location)
        
        return po_data
        
    except Exception as e:
        st.error(f"Error during PO generation: {str(e)}")
        st.exception(e)
        return None

def run_po_generation_tab():
    """Main function for PO Generation tab"""
    
    st.header("Purchase Order Generation")
    
    # Check if required dataframes are available
    required_base_dfs = ['Inventory List', 'Availability Report']
    sales_dfs = [df for df in st.session_state.dataframes.keys() if df.startswith('By Products -')]
    
    # Validation section
    st.subheader("📋 Data Validation")
    
    missing_files = []
    for df in required_base_dfs:
        if df in st.session_state.dataframes:
            st.write(f"✅ {df}")
        else:
            st.write(f"❌ {df}")
            missing_files.append(df)
    
    if len(sales_dfs) >= 4:  # Need all 4 sales metrics
        st.write(f"✅ By Products Data ({len(sales_dfs)} datasets available)")
    else:
        st.write("❌ By Products Data (Need Sales by Product Details Report)")
        missing_files.append("By Products Data")
    
    # Check for replenishment reports
    replenishment_nc = any('Replenishment Report - NC' in df for df in st.session_state.dataframes.keys())
    replenishment_ca = any('Replenishment Report - CA' in df for df in st.session_state.dataframes.keys())
    
    if replenishment_nc:
        st.write("✅ NC Replenishment Report")
    else:
        st.write("❌ NC Replenishment Report")
        
    if replenishment_ca:
        st.write("✅ CA Replenishment Report")
    else:
        st.write("❌ CA Replenishment Report")
    
    # Supplier Management Section
    # Load current excluded suppliers for display
    if 'excluded_suppliers' not in st.session_state:
        load_excluded_suppliers()  # Initialize with defaults
    
    supplier_count = len(st.session_state.excluded_suppliers)
    st.info(f"🚫 Currently excluding {supplier_count} suppliers from purchase orders. Use the 'Supplier Management' tab to modify the list.")
    
    # Processing section
    st.subheader("🚀 Generate Purchase Orders")
    
    # Location selection
    location = st.selectbox(
        "Select Warehouse Location:",
        ["NC", "CA"],
        help="Choose which warehouse to generate purchase orders for"
    )
    
    # Check if we have the required replenishment data for selected location
    has_replenishment = any(f'Replenishment Report - {location}' in df for df in st.session_state.dataframes.keys())
    
    if not has_replenishment:
        st.warning(f"⚠️ Missing Replenishment Report for {location} warehouse. Please upload the required file.")
        processing_enabled = False
    elif missing_files:
        st.warning(f"⚠️ Missing required data files: {', '.join(missing_files)}")
        processing_enabled = False
    else:
        st.success("✅ All required data loaded successfully!")
        processing_enabled = True
    
    # Initialize session state for PO results
    if 'po_results' not in st.session_state:
        st.session_state.po_results = {}
    
    # Processing button
    if st.button(f"Generate {location} Purchase Order", disabled=not processing_enabled, type="primary"):
        if processing_enabled:
            with st.spinner(f"Generating purchase order for {location} warehouse..."):
                po_data = run_po_generation(st.session_state.dataframes, location)
                
                if po_data is not None and len(po_data) > 0:
                    # Store results in session state
                    st.session_state.po_results[location] = po_data
                    st.success(f"✅ Purchase order generated successfully for {location} warehouse!")
                else:
                    st.error("❌ Failed to generate purchase order. Please check your data and try again.")
    
    # Display results if available
    if location in st.session_state.po_results:
        po_data = st.session_state.po_results[location]
        
        st.subheader(f"📋 {location} Purchase Order Results")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Items", len(po_data))
        with col2:
            total_qty = po_data['Quantity*'].sum()
            st.metric("Total Quantity", f"{total_qty:,}")
        with col3:
            unique_suppliers = po_data['SupplierName*'].nunique()
            st.metric("Unique Suppliers", unique_suppliers)
        with col4:
            total_value = (po_data['Quantity*'] * po_data['Price/Amount*']).sum()
            st.metric("Total Value", f"${total_value:,.2f}")
        
        # Display data
        st.dataframe(po_data, use_container_width=True)
        
        # Download option
        csv_data = po_data.to_csv(index=False)
        st.download_button(
            label=f"📥 Download {location} Purchase Order CSV",
            data=csv_data,
            file_name=f"purchase_order_{location.lower()}.csv",
            mime='text/csv'
        )
        
        # Supplier breakdown
        with st.expander("📊 Supplier Breakdown", expanded=False):
            supplier_summary = po_data.groupby('SupplierName*').agg({
                'Quantity*': 'sum',
                'Price/Amount*': lambda x: (po_data.loc[x.index, 'Quantity*'] * x).sum()
            }).round(2)
            supplier_summary.columns = ['Total Quantity', 'Total Value']
            supplier_summary = supplier_summary.sort_values('Total Value', ascending=False)
            st.dataframe(supplier_summary, use_container_width=True)
