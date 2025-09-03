import processing
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        location = sys.argv[1].lower()
        if location not in ['nc', 'ca']:
            print("Invalid location. Please use 'nc' or 'ca'.")
        else:
            processing.run_po_generation('.', location)
    else:
        print("Please provide a location argument (e.g., 'python manual_run.py nc')")
