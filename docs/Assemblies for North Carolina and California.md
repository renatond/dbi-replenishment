Dirty Bird Industries, LLC

# Assemblies for North Carolina and California

## Overview

This guide provides step-by-step instructions for preparing and sending the weekly Assemblies Status report for North Carolina and California.

Important Note
- Ensure RStudio is installed on your computer.
- The scripts ip-rep-nc.R, and ip-rep-ca.R must be run using Rscript.

Reference Sheets & Tools

- DBI: Assembly Orders with TO (NC)
- DBI: Assembly Orders with TO (CA)
- BOM Component Availability Report (DEAR Systems)
- Product Availability Report (DEAR Systems)

## Step-by-Step by Guide

### Step 1: Update the BOM Report Tab

- Go to the BOM Report tab.
- Update the data only once per month.

### Step 2: Update the Product Availability Tab

1.  Download the availability report from: DEAR Systems – Stock
2.  Open the downloaded file.
    -  Delete all columns beyond the "Allocated" column.

3.  In the Product Availability tab:

    - Go to File > Import
    - Select the cleaned file
    - Choose Append to current sheet
    - After importing, set SKU column to Plain Text

### Step 3: Clear the Input Tab

- In the Input tab, clear columns A to F before adding new data.

### Step 4: Filter for NC/CA Availability

- Go to the Analysis tab.
- In Column P (Available in NC/CA):
    - Use filter by cell color (Red) to find relevant rows.

### Step 5: Copy Data to Input Tab

- Copy columns M to R of the filtered rows.
- Paste as Values Only into the Input tab.
- In the Input tab, drag down formulas in Column G to apply to the new rows.

### Step 6: Update Assemblies Status Computation

- In the Assemblies Status Computation tab:

    - Copy the formula in cell F3.
    - Paste it to cell F4 and downward to update the rest of the column.

### Step 7: Create the Email

- Use the previous email template as a reference.
- Update the Subject Line with the current date.

### Step 8: Prepare the Report for Email

- In the Reports tab, For North Carolina, copy the following ranges:
    - Columns E to I
    - Columns K to M
    - Columns X to AC
    - Columns AE to AJ
- For California, copy:
    - Columns E to I
- Paste these tables into the email as shown in previous emails.

### Step 9: Send the Email

- Copy the recipients from the previous email.
- Double-check the email date and details.
- Send the email once all contents are verified.