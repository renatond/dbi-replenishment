import streamlit as st

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
    return st.session_state.excluded_suppliers

def run_supplier_management():
    """Main function for Supplier Management tab"""
    
    st.header("🚫 Excluded Suppliers Management")
    
    st.markdown("""
    Configure suppliers to exclude from all purchase orders. This helps prevent orders from:
    - Internal transfer accounts
    - Problematic vendors
    - Discontinued supplier accounts
    - Testing/development accounts
    """)
    
    # Load current excluded suppliers
    load_excluded_suppliers()  # Initialize if not exists
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Excluded Suppliers", len(st.session_state.excluded_suppliers))
    with col2:
        # Count how many are from default list
        default_suppliers = [
            'auto transfer', 'direct transfer', 'internal transfer', 'transfer in',
            'transfer out', 'stock adjustment', 'inventory adjustment', 'write off',
            'damaged goods', 'lost inventory', 'returned goods', 'customer return',
            'warranty replacement', 'sample product', 'promotional item', 'gift',
            'complimentary', 'testing', 'quality control', 'research', 'development',
            'prototype', 'discontinued', 'obsolete', 'end of life', 'clearance',
            'liquidation', 'bulk sale'
        ]
        default_count = len([s for s in st.session_state.excluded_suppliers if s.lower() in default_suppliers])
        st.metric("Default Exclusions", default_count)
    with col3:
        custom_count = len(st.session_state.excluded_suppliers) - default_count
        st.metric("Custom Exclusions", custom_count)
    
    st.divider()
    
    # Main editing interface
    st.subheader("📝 Edit Excluded Suppliers")
    
    # Text area for editing suppliers
    suppliers_text = st.text_area(
        "Excluded Suppliers (one per line):",
        value='\n'.join(st.session_state.excluded_suppliers),
        height=400,
        help="Enter supplier names to exclude from purchase orders. Matching is case-insensitive."
    )
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Changes", type="primary", use_container_width=True):
            # Update session state
            new_suppliers = [line.strip() for line in suppliers_text.split('\n') if line.strip()]
            old_count = len(st.session_state.excluded_suppliers)
            st.session_state.excluded_suppliers = new_suppliers
            new_count = len(new_suppliers)
            
            if new_count != old_count:
                st.success(f"✅ Updated excluded suppliers list: {old_count} → {new_count} suppliers")
            else:
                st.success("✅ Excluded suppliers list saved successfully")
            st.rerun()
    
    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            # Reset to default list
            st.session_state.excluded_suppliers = [
                'auto transfer', 'direct transfer', 'internal transfer', 'transfer in',
                'transfer out', 'stock adjustment', 'inventory adjustment', 'write off',
                'damaged goods', 'lost inventory', 'returned goods', 'customer return',
                'warranty replacement', 'sample product', 'promotional item', 'gift',
                'complimentary', 'testing', 'quality control', 'research', 'development',
                'prototype', 'discontinued', 'obsolete', 'end of life', 'clearance',
                'liquidation', 'bulk sale'
            ]
            st.success("✅ Reset to default excluded suppliers list")
            st.rerun()
    
    with col3:
        if st.button("🗑️ Clear All", use_container_width=True):
            if st.session_state.get('confirm_clear', False):
                st.session_state.excluded_suppliers = []
                st.session_state.confirm_clear = False
                st.success("✅ Cleared all excluded suppliers")
                st.rerun()
            else:
                st.session_state.confirm_clear = True
                st.warning("⚠️ Click again to confirm clearing all suppliers")
                st.rerun()
    
    # Preview section
    st.divider()
    st.subheader("👀 Current Excluded Suppliers")
    
    if st.session_state.excluded_suppliers:
        # Create a searchable/filterable view
        search_term = st.text_input("🔍 Search suppliers:", placeholder="Type to filter...")
        
        if search_term:
            filtered_suppliers = [s for s in st.session_state.excluded_suppliers 
                                if search_term.lower() in s.lower()]
        else:
            filtered_suppliers = st.session_state.excluded_suppliers
        
        if filtered_suppliers:
            # Display in columns for better readability
            cols = st.columns(3)
            for i, supplier in enumerate(sorted(filtered_suppliers)):
                with cols[i % 3]:
                    st.write(f"• {supplier}")
        else:
            st.info("No suppliers match your search.")
    else:
        st.info("No suppliers are currently excluded.")
    
    # Help section
    st.divider()
    st.subheader("❓ Help & Guidelines")
    
    with st.expander("How Excluded Suppliers Work", expanded=False):
        st.markdown("""
        **Exclusion Process:**
        - Supplier names are matched case-insensitively
        - Partial matches are supported (e.g., "transfer" matches "Auto Transfer")
        - Excluded suppliers are filtered out during PO generation
        - Changes apply to all future purchase orders
        
        **Common Exclusions:**
        - **Internal Transfers**: Auto Transfer, Direct Transfer, Stock Adjustment
        - **Returns/Damaged**: Customer Return, Warranty Replacement, Damaged Goods
        - **Testing/Development**: Testing, Quality Control, Research, Prototype
        - **Discontinued**: Obsolete, End of Life, Clearance, Liquidation
        
        **Best Practices:**
        - Use lowercase for consistency
        - Include common variations (e.g., both "transfer" and "transfers")
        - Review the list periodically to remove outdated exclusions
        - Test with a small PO generation to verify exclusions work correctly
        """)
    
    with st.expander("Import/Export Suppliers", expanded=False):
        st.markdown("**Export Current List:**")
        if st.session_state.excluded_suppliers:
            export_text = '\n'.join(st.session_state.excluded_suppliers)
            st.download_button(
                label="📥 Download Excluded Suppliers List",
                data=export_text,
                file_name="excluded_suppliers.txt",
                mime="text/plain"
            )
        else:
            st.info("No suppliers to export.")
        
        st.markdown("**Import from File:**")
        uploaded_file = st.file_uploader(
            "Upload suppliers list (text file, one per line)",
            type=['txt'],
            help="Upload a text file with one supplier name per line"
        )
        
        if uploaded_file is not None:
            try:
                content = uploaded_file.read().decode('utf-8')
                imported_suppliers = [line.strip() for line in content.split('\n') if line.strip()]
                
                if imported_suppliers:
                    st.write(f"**Preview import:** {len(imported_suppliers)} suppliers found")
                    preview_text = '\n'.join(imported_suppliers[:10])
                    if len(imported_suppliers) > 10:
                        preview_text += f"\n... and {len(imported_suppliers) - 10} more"
                    st.text(preview_text)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📥 Import (Replace All)", key="import_replace"):
                            st.session_state.excluded_suppliers = imported_suppliers
                            st.success(f"✅ Imported {len(imported_suppliers)} suppliers (replaced existing list)")
                            st.rerun()
                    
                    with col2:
                        if st.button("📥 Import (Add to Existing)", key="import_add"):
                            # Combine and deduplicate
                            combined = list(set(st.session_state.excluded_suppliers + imported_suppliers))
                            old_count = len(st.session_state.excluded_suppliers)
                            st.session_state.excluded_suppliers = sorted(combined)
                            new_count = len(combined)
                            st.success(f"✅ Added {new_count - old_count} new suppliers (total: {new_count})")
                            st.rerun()
                else:
                    st.warning("No valid suppliers found in the uploaded file.")
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
