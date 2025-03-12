# BlobHunter

A Python-based security tool for discovering public blob containers in Azure Storage accounts across all subscriptions in a tenant.

## Recent Updates

- Fixed array index out of range issue with tenant and subscription mapping
- Improved tenant name resolution using dictionary-based approach
- Added better handling for unknown tenant names
- Enhanced subscription selection logic

## Prerequisites

- Python 3.6 or higher
- PowerShell 7 (pwsh)
- Azure CLI installed and configured
- Required Python packages:
  - azure-identity
  - azure-mgmt-resource
  - azure-mgmt-storage
  - azure-storage-blob
  - pyinputplus

## Azure Role Requirements

The tool requires an Azure user with one of the following built-in roles:
- Owner
- Contributor
- Storage Account Contributor

Alternatively, any Azure user with permissions to perform these specific actions:
- Microsoft.Resources/subscriptions/read
- Microsoft.Resources/subscriptions/resourceGroups/read
- Microsoft.Storage/storageAccounts/read
- Microsoft.Storage/storageAccounts/listkeys/action
- Microsoft.Storage/storageAccounts/blobServices/containers/read
- Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read

## Installation

1. Install Azure CLI from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
2. Install PowerShell 7 from: https://aka.ms/powershell-release?tag=stable
3. Install required Python packages:
```bash
pip install azure-identity azure-mgmt-resource azure-mgmt-storage azure-storage-blob pyinputplus
```

## Usage

1. Login to Azure CLI:
```bash
az login
```

2. Run the script:
```bash
python BlobHunter.py
```

3. Choose scanning options:
   - 'Y' to scan all available subscriptions
   - 'N' to select specific subscriptions to scan

## Output

The script generates a CSV file named `public-containers-{date}.csv` containing:
- Tenant ID
- Tenant Name
- Subscription ID
- Subscription Name
- Resource Group
- Storage Account
- Container
- Public Access Level
- URL
- Total Files
- File counts by extension (txt, csv, pdf, docx, xlsx, others)

## Code Structure

- `print_logo()`: Displays the tool banner
- `setup_azure_cli_path()`: Configures Azure CLI environment
- `get_credentials()`: Handles Azure authentication
- `get_tenants_and_subscriptions()`: Maps tenants and subscriptions
- `choose_subscriptions()`: Handles subscription selection
- `check_subscription()`: Scans individual subscriptions
- `check_storage_account()`: Analyzes storage accounts
- `iterator_wrapper()`: Handles API pagination and throttling
- `count_files_extensions()`: Analyzes file types in containers
- `write_csv()`: Generates the report file

## Error Handling

- Azure CLI installation check
- PowerShell 7 verification
- Login state validation
- API throttling management
- Permission checking for storage accounts
- Tenant name resolution with fallback

## Authors

- Original Author: Daniel Niv
- Modified by: Johnny Monteleone
