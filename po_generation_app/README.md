# Purchase Order Generation App

## Overview

This application automates the process of generating weekly purchase orders for Dirty Bird Industries. It takes various sales, inventory, and replenishment reports as input, applies business logic to calculate necessary order quantities, and generates a CSV file that can be directly imported into Cin7 Core.

The application can be run in two ways: through a simple web interface or as a command-line script.

---

## For End-Users

### How to Use the Web Application

The web interface is the easiest way to use the application.

1.  **Start the Server**: Open a terminal or command prompt and run the following command from the project's main directory:
    ```bash
    python3 app.py
    ```
2.  **Access the Interface**: Open a web browser and navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000).
3.  **Upload Files**: Click the "Choose Files" button and select all of your weekly report files. The application will process them automatically.
4.  **Download PO File**: Once processing is complete, a download link will appear. Click it to download your `purchase_order.csv` file.

### How to Use the Manual Script

If you prefer to run the process from the command line, you can use the `manual_run.py` script. This is particularly useful for generating a PO for a specific warehouse location.

1.  **Run from Terminal**: Open a terminal and run the script with the desired location code (`nc` or `ca`):
    ```bash
    # For North Carolina
    python3 manual_run.py nc

    # For California
    python3 manual_run.py ca
    ```
2.  **Find Your File**: The script will generate a location-specific purchase order file in the project directory (e.g., `purchase_order_nc.csv`).

### Input File Requirements

For the application to work correctly, you must provide the following files. The filenames should follow the patterns listed below.

#### 1. Sales Reports from DEAR Systems
**Choose ONE of these options:**

**Option A: Combined Report (Recommended)**
- **Filename**: `Sales by Product Details Report.xlsx`
- **Instructions**: Export the complete report with all metrics (Sales, COGS, Profit, Quantity)
- **Format**: Single Excel file with data starting on row 6, columns arranged as: SKU | Sale | Quantity | COGS | Profit (repeating for each month)

**Option B: Separate Reports (Legacy Support)**  
- **Filenames**: 
    - `Sales by Product Details Report - Sales.xlsx`
    - `Sales by Product Details Report - COGS.xlsx` 
    - `Sales by Product Details Report - Profit.xlsx`
    - `Sales by Product Details Report - Quantity.xlsx`
- **Format**: Each file has 4 header rows, with SKU in first column and months as subsequent columns

#### 2. Replenishment Report (CSV)
- **Filename Pattern**: `replenishment-Combined [LOCATION] Warehouses-variants-*.csv` (e.g., `replenishment-Combined NC Warehouses-variants-2024.07.01-2025.08.31.24.csv`)
- **Required Columns**:
    - `SKU`: The product stock-keeping unit
    - `Lead time`: The supplier lead time in days
    - `Adjusted sales velocity/day`: The baseline daily sales velocity for the product
    - `Cost price`: The cost of the product

#### 3. Inventory List (CSV)
- **Filename Pattern**: `InventoryList_*.csv`
- **Required Columns**:
    - `ProductCode`: The SKU of the product.
    - `LastSuppliedBy`: The name of the default supplier for the product.

#### 4. Availability Report (CSV)
- **Filename Pattern**: `AvailabilityReport_*.csv`
- **Required Columns**:
    - `SKU`: The product stock-keeping unit.
    - `Location`: The warehouse location (e.g., `NC - Main`).
    - `Available`: The current available stock quantity.
    - `OnOrder`: The quantity of stock currently on order from suppliers.

---

## Key Features

### 🏢 Multi-Warehouse Support
The application supports generating purchase orders for both North Carolina (NC) and California (CA) warehouses independently. Users select the warehouse location via radio buttons in the web interface.

### 📊 Enhanced Purchase Order Output
Generated purchase orders include comprehensive information:

| Column | Source | Description |
|--------|--------|-------------|
| `RecordType*` | System | Always "Order" for Cin7 Core import |
| `SupplierName*` | InventoryList | Primary supplier for the product |
| `SupplierProductCode` | InventoryList | Supplier's internal product code |
| `Product*` | Replenishment | Your internal SKU |
| `ProductName` | InventoryList | Full product description |
| `Quantity*` | Calculated | Final order quantity after all adjustments |
| `Price/Amount*` | Replenishment | Cost price per unit |
| `Lead time` | Replenishment | Supplier lead time in days |
| `Adjusted Monthly Sales` | Calculated | Sales velocity per day × 30 |

### 🚫 Supplier Exclusion Management
- **Web Interface**: Easily manage excluded suppliers via `/manage-suppliers` page
- **Real-Time Filtering**: Excluded suppliers are automatically removed from all POs
- **27 Pre-Configured Exclusions**: Includes problematic vendors, internal transfers, etc.
- **Case-Insensitive**: Matching works regardless of capitalization
- **Persistent Storage**: Exclusions saved in `excluded_suppliers.txt`

### 🔧 Intelligent File Processing
- **Combined File Support**: Uses single `Sales by Product Details Report.xlsx` (recommended)
- **Backward Compatibility**: Still supports 4 separate Excel files 
- **Smart Detection**: Automatically detects file format and processes accordingly
- **Robust Stock Aggregation**: Combines stock from multiple bin locations per warehouse
- **On-Order Integration**: Factors in existing purchase orders to prevent over-ordering

### 📈 Advanced Business Logic
- **Margin-Adjusted Sales Velocity**: Applies tiered velocity adjustments based on product price and profit margin
- **Dynamic Stock Calculation**: `Days of Stock = Lead Time + 3 days` safety buffer
- **Available Stock Consideration**: `PO Quantity = Target Stock - Available Stock - On Order Stock`

---

## For Developers

### Project Setup

1.  **Prerequisites**: Python 3.9+ and `venv`.
2.  **Create Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Project Structure

-   `app.py`: The Flask web server. Provides the user interface for file uploads and downloads.
-   `processing.py`: The core data processing logic. Contains all the functions for loading, cleaning, merging, and calculating the purchase order data.
-   `manual_run.py`: A command-line interface for running the processing logic directly.
-   `templates/index.html`: The HTML template for the web interface.
-   `requirements.txt`: A list of all the Python dependencies.
-   `Dockerfile`: For containerizing the application.

### Core Logic (`processing.py`)

The data processing pipeline is orchestrated by the `run_po_generation` function and follows these steps:
1.  **Load Data**: Each source file is loaded into a pandas DataFrame. During this step, data is cleaned (e.g., SKUs are normalized) and pre-processed (e.g., stock is aggregated by location).
2.  **Merge Data**: All DataFrames are merged into a single master DataFrame, using the `SKU` as the primary key.
3.  **Calculate Metrics**:
    -   `calculate_profit_margin()`: Calculates the profit margin from the sales and profit data.
    -   `adjust_sales_velocity()`: Applies the tiered margin adjustments to the baseline sales velocity.
    -   `calculate_po_quantity()`: Calculates the final PO quantity, factoring in lead time, available stock, and on-order stock.
4.  **Generate CSV**: The final DataFrame is formatted to match the Cin7 Core import template and saved as a CSV file.

### Running with Docker

The application can be built and run as a Docker container for easy deployment.

1.  **Build the Image**:
    ```bash
    docker build -t po-generator .
    ```
2.  **Run the Container**:
    ```bash
    docker run -p 5000:5000 po-generator
    ```
The application will then be available at [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

### Deploying to Azure App Service

You can deploy this application as a containerized web app on Azure. You will need the [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) and Docker installed.

1.  **Login to Azure**:
    ```bash
    az login
    ```

2.  **Create a Resource Group**:
    Replace `MyResourceGroup` with a name for your resource group and `eastus` with your preferred location.
    ```bash
    az group create --name MyResourceGroup --location eastus
    ```

3.  **Create an Azure Container Registry (ACR)**:
    Replace `myacrname` with a unique name for your container registry.
    ```bash
    az acr create --resource-group MyResourceGroup --name myacrname --sku Basic --admin-enabled true
    ```

4.  **Build and Push the Docker Image to ACR**:
    ```bash
    # Login to your ACR
    az acr login --name myacrname

    # Build the Docker image
    docker build -t po-generator .

    # Tag the image for ACR
    docker tag po-generator myacrname.azurecr.io/po-generator:latest

    # Push the image to ACR
    docker push myacrname.azurecr.io/po-generator:latest
    ```

5.  **Create an App Service Plan**:
    Replace `MyAppServicePlan` with a name for your plan.
    ```bash
    az appservice plan create --name MyAppServicePlan --resource-group MyResourceGroup --is-linux --sku B1
    ```

6.  **Create the Web App**:
    Replace `mywebappname` with a unique name for your web app.
    ```bash
    az webapp create --resource-group MyResourceGroup --plan MyAppServicePlan --name mywebappname --deployment-container-image-name myacrname.azurecr.io/po-generator:latest
    ```

7.  **Configure the Web App to Use ACR**:
    ```bash
    az webapp config container set --name mywebappname --resource-group MyResourceGroup --docker-registry-server-url https://myacrname.azurecr.io --docker-registry-server-user $(az acr credential show -n myacrname --query username --output tsv) --docker-registry-server-password $(az acr credential show -n myacrname --query passwords[0].value --output tsv)
    ```

After these steps, your application will be deployed and accessible at `http://mywebappname.azurewebsites.net`.

---

## Live Application & DevOps Pipeline

### 🚀 Production Application
The application is currently deployed and accessible at:
**https://dbi-po-generation-app.azurewebsites.net**

### 🔄 Automatic Deployment Pipeline

This project includes a complete CI/CD pipeline using GitHub Actions and Azure services:

#### How It Works
1. **Code Changes**: When you push changes to the `main` branch on GitHub
2. **Automatic Build**: GitHub Actions automatically triggers a build process
3. **Container Build**: The application is built as a Docker container in Azure Container Registry
4. **Auto Deploy**: The new container is automatically deployed to Azure App Service
5. **Zero Downtime**: The deployment process ensures your application remains available during updates

#### GitHub Actions Workflow
The deployment workflow is defined in `.github/workflows/azure-deploy.yml` and includes:
- Building the Docker image in Azure Container Registry (no local Docker required)
- Pushing the image with a unique tag for each deployment
- Deploying the new version to Azure App Service

#### Azure Resources Created
- **Resource Group**: `dbi-po-generation-rg`
- **Container Registry**: `dbipogenerationacr.azurecr.io`
- **App Service Plan**: `dbi-po-generation-plan` (Linux B1 tier)
- **Web App**: `dbi-po-generation-app`

#### Required GitHub Secrets
The following secrets are configured in your GitHub repository for automatic deployments:
- `AZURE_CREDENTIALS`: Service principal credentials for Azure authentication
- `REGISTRY_USERNAME`: Azure Container Registry username
- `REGISTRY_PASSWORD`: Azure Container Registry password

### 🛠️ Managing the Deployment

#### To Deploy Changes
Simply push your changes to the main branch:
```bash
git add .
git commit -m "Your change description"
git push origin main
```
The application will automatically update within 2-5 minutes.

#### To Monitor Deployments
- Go to your GitHub repository > Actions tab to see deployment status
- Check the Azure App Service logs in the Azure portal for runtime issues

#### To Update Configuration
If you need to modify Azure resources or GitHub secrets:
- Use the Azure CLI commands shown above
- Use `gh secret set SECRET_NAME --body "value"` to update GitHub secrets
