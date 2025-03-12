# BlobHunter

A tool for scanning Azure Storage Accounts for publicly accessible containers.

## Prerequisites

- Python 3.x
- PowerShell 7 ([Download](https://aka.ms/powershell-release?tag=stable))
- Azure CLI ([Download](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli))

## Installation

1. Clone the repository
2. Create a virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Recent Updates

- Added PowerShell 7 support for Azure CLI commands
- Improved Azure CLI path handling
- Added automatic Azure CLI path detection
- Added better error handling for Azure CLI installation checks

## Usage

1. Ensure Azure CLI is installed and in PATH
2. Run the script:
```bash
python BlobHunter/BlobHunter.py
```

## Troubleshooting

If you encounter Azure CLI path issues:
1. Verify Azure CLI is installed
2. The script will automatically attempt to add the Azure CLI path
3. Default Azure CLI paths checked:
   - C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin
   - C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin

## Authors

- Original Author: Daniel Niv
- Modified by: Johnny Monteleone
