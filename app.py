import streamlit as st
import pandas as pd
import io

# Configure the page
st.set_page_config(
    page_title="DBI Stock Orders Manager",
    page_icon="📦",
    layout="wide"
)

# Main title
st.title("DBI Stock Orders Manager")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["Upload Database", "PO Generation", "Assembly Order Generation", "Supplier Management"])

with tab1:
    st.header("Upload Database")
    
    # File uploader for multiple xlsx and csv files
    uploaded_files = st.file_uploader(
        "Choose Excel or CSV files",
        type=['xlsx', 'csv'],
        accept_multiple_files=True,
        help="You can upload multiple Excel (.xlsx) and CSV (.csv) files at once"
    )
    
    # Initialize session state for dataframes if not exists
    if 'dataframes' not in st.session_state:
        st.session_state.dataframes = {}
    
    # Function to clean dataframes
    def clean_dataframe(df):
        """Remove Unnamed columns and drop columns that are entirely NaN"""
        # Remove columns starting with 'Unnamed'
        unnamed_cols = [col for col in df.columns if str(col).startswith('Unnamed')]
        if unnamed_cols:
            df = df.drop(columns=unnamed_cols)
        
        # Drop columns that are entirely NaN
        df = df.dropna(axis=1, how='all')
        
        return df
    
    # Function to parse files based on naming patterns
    def parse_uploaded_files(files):
        dataframes = {}
        parsed_files = []
        
        for file in files:
            filename = file.name
            file_content = file.read()
            file.seek(0)  # Reset file pointer
            
            try:
                # Availability Report
                if filename.startswith("AvailabilityReport_"):
                    df = pd.read_csv(io.BytesIO(file_content))
                    df = clean_dataframe(df)
                    dataframes["Availability Report"] = df
                    parsed_files.append(("Availability Report", filename, "✅"))
                
                # BOM Report (skip first 2 rows)
                elif "BOM Component Availability" in filename and filename.endswith('.xlsx'):
                    df = pd.read_excel(io.BytesIO(file_content), skiprows=2)
                    df = clean_dataframe(df)
                    dataframes["BOM Report"] = df
                    parsed_files.append(("BOM Report", filename, "✅"))
                
                # Inventory List
                elif filename.startswith("InventoryList_"):
                    df = pd.read_csv(io.BytesIO(file_content))
                    df = clean_dataframe(df)
                    dataframes["Inventory List"] = df
                    parsed_files.append(("Inventory List", filename, "✅"))
                
                # Replenishment Report - NC
                elif "replenishment-Combined NC Warehouses" in filename or "replenishment-Combined_NC_Warehouses" in filename:
                    df = pd.read_csv(io.BytesIO(file_content))
                    # Clean up SKU column (remove Excel quotes if present)
                    if 'SKU' in df.columns:
                        df['SKU'] = df['SKU'].astype(str).str.replace('="', '').str.replace('"', '')
                    df = clean_dataframe(df)
                    dataframes["Replenishment Report - NC"] = df
                    parsed_files.append(("Replenishment Report - NC", filename, "✅"))
                
                # Replenishment Report - CA
                elif "replenishment-Combined CA Warehouses" in filename or "replenishment-Combined_CA_Warehouses" in filename:
                    df = pd.read_csv(io.BytesIO(file_content))
                    # Clean up SKU column (remove Excel quotes if present)
                    if 'SKU' in df.columns:
                        df['SKU'] = df['SKU'].astype(str).str.replace('="', '').str.replace('"', '')
                    df = clean_dataframe(df)
                    dataframes["Replenishment Report - CA"] = df
                    parsed_files.append(("Replenishment Report - CA", filename, "✅"))
                
                # Sales by Product Details Report (skip first 4 rows, handle multi-index)
                elif "Sales by Product Details Report" in filename and filename.endswith('.xlsx'):
                    # Read with multi-index columns, skip first 4 rows
                    df = pd.read_excel(io.BytesIO(file_content), skiprows=4, header=[0, 1])
                    df = clean_dataframe(df)
                    
                    # Extract the different metrics as separate dataframes
                    if len(df.columns.levels) == 2:  # Confirm it's multi-index
                        # Get the first column data and name (usually SKU or product identifier)
                        first_col_data = df.iloc[:, 0]
                        first_col_name = df.columns[0]
                        
                        # Extract the clean column name (handle multi-index column name)
                        if isinstance(first_col_name, tuple):
                            # For multi-index, use the first non-empty part
                            clean_first_col_name = next((part for part in first_col_name if str(part) != 'nan' and str(part).strip()), 'SKU')
                        else:
                            clean_first_col_name = str(first_col_name)
                        
                        # If the column name is still unclear, default to 'SKU'
                        if clean_first_col_name in ['Unnamed: 0', '0', 'nan'] or 'Unnamed' in str(clean_first_col_name):
                            clean_first_col_name = 'SKU'
                        
                        # Extract each metric type
                        metrics = ['Sale', 'Quantity', 'COGS', 'Profit']
                        
                        for metric in metrics:
                            try:
                                # Get columns that have the metric in the second level
                                metric_cols = [col for col in df.columns if len(col) > 1 and col[1] == metric]
                                if metric_cols:
                                    # Create dataframe with first column and metric columns
                                    metric_df = pd.DataFrame()
                                    
                                    # Add the SKU/identifier column
                                    metric_df[clean_first_col_name] = first_col_data
                                    
                                    # Add metric columns with month names
                                    for col in metric_cols:
                                        month = col[0]  # Month name from first level
                                        metric_df[month] = df[col]
                                    
                                    # Clean the metric dataframe
                                    metric_df = clean_dataframe(metric_df)
                                    
                                    # Ensure the first column is treated as SKU for consistency
                                    if clean_first_col_name != 'SKU':
                                        metric_df = metric_df.rename(columns={clean_first_col_name: 'SKU'})
                                    
                                    dataframes[f"Sales - {metric}"] = metric_df
                                    
                            except Exception as e:
                                st.warning(f"Error processing {metric} data: {str(e)}")
                                st.exception(e)
                        
                        parsed_files.append(("Sales by Product Details Report", filename, "✅ (Split into metrics)"))
                    else:
                        # Fallback: treat as regular dataframe
                        df = clean_dataframe(df)
                        dataframes["Sales by Product Details Report"] = df
                        parsed_files.append(("Sales by Product Details Report", filename, "✅"))
                
                else:
                    parsed_files.append(("Unknown", filename, "❌ (Pattern not recognized)"))
                    
            except Exception as e:
                parsed_files.append(("Error", filename, f"❌ Error: {str(e)}"))
        
        return dataframes, parsed_files
    
    # Process uploaded files
    if uploaded_files:
        st.subheader("Processing Files...")
        
        # Parse the files
        new_dataframes, file_status = parse_uploaded_files(uploaded_files)
        
        # Update session state with new dataframes
        st.session_state.dataframes.update(new_dataframes)
        
        # Display file processing status
        st.subheader("File Processing Status:")
        for report_type, filename, status in file_status:
            col1, col2, col3 = st.columns([2, 3, 1])
            with col1:
                st.write(f"**{report_type}**")
            with col2:
                st.write(filename)
            with col3:
                st.write(status)
        
        st.success(f"Successfully processed {len(uploaded_files)} file(s)")
        
    # Display dataframes if any exist
    if st.session_state.dataframes:
        st.subheader("Available Datasets:")
        
        # Dropdown to select dataframe
        df_names = list(st.session_state.dataframes.keys())
        selected_df_name = st.selectbox("Select a dataset to view:", df_names)
        
        if selected_df_name:
            df = st.session_state.dataframes[selected_df_name]
            
            # Show basic info about the dataframe
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
            
            # Display the dataframe
            st.subheader(f"Data Preview: {selected_df_name}")
            st.dataframe(df, use_container_width=True)
            
            # Option to download as CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label=f"Download {selected_df_name} as CSV",
                data=csv,
                file_name=f"{selected_df_name.replace(' ', '_').replace('-', '_')}.csv",
                mime='text/csv'
            )
    else:
        if not uploaded_files:
            st.info("👆 Please upload files to get started")
        else:
            st.warning("No recognized file patterns found in uploaded files")

with tab2:
    import po_generation
    po_generation.run_po_generation_tab()

with tab3:
    import assembly_order_generation
    assembly_order_generation.run_assembly_order_generation()

with tab4:
    import supplier_management
    supplier_management.run_supplier_management()
