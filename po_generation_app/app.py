from flask import Flask, request, render_template, send_from_directory, redirect, url_for
import os
import processing 

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Clear the upload folder before new uploads
        for f in os.listdir(UPLOAD_FOLDER):
            os.remove(os.path.join(UPLOAD_FOLDER, f))

        # Get the selected warehouse location
        location = request.form.get('location', 'nc')  # Default to 'nc' if not specified
        
        files = request.files.getlist('files')
        uploaded_files = []
        for file in files:
            if file.filename != '':
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
                uploaded_files.append(file.filename)
        
        print(f"DEBUG: Uploaded files: {uploaded_files}")
        print(f"DEBUG: Looking for {location.upper()} warehouse files in {UPLOAD_FOLDER}")
        
        try:
            output_filename = processing.run_po_generation(UPLOAD_FOLDER, location)
            if output_filename:
                return f"""
                <div style="text-align: center; padding: 50px; font-family: sans-serif;">
                    <h2>✅ Purchase Order Generated Successfully!</h2>
                    <p>Location: <strong>{location.upper()} Warehouse</strong></p>
                    <p>Files processed: {len([f for f in files if f.filename])}</p>
                    <br>
                    <a href="/download/{output_filename}" style="background: #27ae60; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">📥 Download {location.upper()} Purchase Order</a>
                    <br><br>
                    <a href="/" style="color: #3498db;">← Generate Another PO</a>
                </div>
                """
            else:
                return f"""
                <div style="text-align: center; padding: 50px; font-family: sans-serif;">
                    <h2>❌ Error Processing Files</h2>
                    <p>Could not generate PO for {location.upper()} warehouse. Please check that all required files are uploaded and try again.</p>
                    <a href="/" style="color: #3498db;">← Try Again</a>
                </div>
                """
        except Exception as e:
            return f"""
            <div style="text-align: center; padding: 50px; font-family: sans-serif;">
                <h2>❌ Error Processing Files</h2>
                <p>An error occurred: {str(e)}</p>
                <a href="/" style="color: #3498db;">← Try Again</a>
            </div>
            """
    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('.', filename, as_attachment=True)

@app.route('/manage-suppliers', methods=['GET', 'POST'])
def manage_suppliers():
    if request.method == 'POST':
        # Save the updated supplier list
        suppliers_text = request.form.get('suppliers', '')
        suppliers_list = [line.strip() for line in suppliers_text.split('\n') if line.strip()]
        
        try:
            with open('excluded_suppliers.txt', 'w') as f:
                f.write('\n'.join(suppliers_list))
            return render_template('manage_suppliers.html', 
                                 suppliers_text='\n'.join(suppliers_list),
                                 supplier_count=len(suppliers_list),
                                 message="✅ Excluded suppliers list updated successfully!")
        except Exception as e:
            return render_template('manage_suppliers.html', 
                                 suppliers_text=suppliers_text,
                                 supplier_count=len(suppliers_list),
                                 message=f"❌ Error saving suppliers: {str(e)}")
    
    # Load current suppliers for display
    try:
        if os.path.exists('excluded_suppliers.txt'):
            with open('excluded_suppliers.txt', 'r') as f:
                suppliers_text = f.read().strip()
                supplier_count = len([line for line in suppliers_text.split('\n') if line.strip()])
        else:
            suppliers_text = ''
            supplier_count = 0
    except Exception as e:
        suppliers_text = f'Error loading suppliers: {str(e)}'
        supplier_count = 0
    
    return render_template('manage_suppliers.html', 
                         suppliers_text=suppliers_text,
                         supplier_count=supplier_count)

if __name__ == '__main__':
    # Use PORT environment variable for Azure, default to 5000 for local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
