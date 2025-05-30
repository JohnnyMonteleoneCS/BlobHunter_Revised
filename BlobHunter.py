import itertools
import time
import pyinputplus as pyip
import azure.core.exceptions
from datetime import date
from azure.identity import AzureCliCredential
from azure.mgmt.resource import SubscriptionClient, ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient, ContainerClient
import subprocess
import csv
import os
import sys

ENDPOINT_URL = '{}.blob.core.windows.net'
CONTAINER_URL = '{}.blob.core.windows.net/{}/'
EXTENSIONS = ["txt", "csv", "pdf", "docx", "xlsx"]
STOP_SCAN_FLAG = "stop scan"

def find_pwsh():
    """Find PowerShell 7 executable path"""
    possible_paths = [
        "C:\\Program Files\\PowerShell\\7\\pwsh.exe",
        os.path.expandvars("%ProgramFiles%\\PowerShell\\7\\pwsh.exe"),
        os.path.expandvars("%ProgramFiles(x86)%\\PowerShell\\7\\pwsh.exe")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    return None

def setup_azure_cli_path():
    """Add Azure CLI path to current process environment"""
    azure_cli_paths = [
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin",
        r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin",
        os.path.expandvars(r"%ProgramFiles%\Microsoft SDKs\Azure\CLI2\wbin"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft SDKs\Azure\CLI2\wbin")
    ]
    
    for path in azure_cli_paths:
        if os.path.exists(path) and os.path.exists(os.path.join(path, 'az.cmd')):
            if path not in os.environ['PATH']:
                os.environ['PATH'] = path + os.pathsep + os.environ['PATH']
                print(f"[+] Added Azure CLI path: {path}", flush=True)
            return True
            
    return False

def run_az_command(command):
    """Run Azure CLI command using PowerShell 7"""
    pwsh_path = find_pwsh()
    if not pwsh_path:
        print("[-] PowerShell 7 not found. Please install from: https://aka.ms/powershell-release?tag=stable", flush=True)
        return None
    
    if not setup_azure_cli_path():
        print("[-] Azure CLI path not found", flush=True)
        return None
        
    try:
        return subprocess.check_output([pwsh_path, "-Command", command], 
                                    stderr=subprocess.DEVNULL,
                                    env=os.environ).decode("utf-8")
    except subprocess.CalledProcessError as e:
        return None

def check_az_cli():
    result = run_az_command("az --version")
    if result is None:
        print("[-] Azure CLI is not installed or not in PATH", flush=True)
        print("[!] Please install Azure CLI from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli", flush=True)
        print("[!] After installation, restart your terminal and run this script again", flush=True)
        return False
    return True

def get_credentials():
    if not check_az_cli():
        return None
        
    username = run_az_command("az account show --query user.name")
    if not username:
        print("[*] Not logged in. Launching Azure login...", flush=True)
        login_result = run_az_command("az login")
        if not login_result:
            print("[-] Azure CLI login failed. Please try logging in manually using 'az login' in PowerShell 7", flush=True)
            return None
        username = run_az_command("az account show --query user.name")
        
    print("[+] Logged in as user {}".format(username.replace('"', '').replace("\n", '')), flush=True)
    return AzureCliCredential()

def get_tenants_and_subscriptions(creds):
    subscription_client = SubscriptionClient(creds)
    tenants_dict = {}  # Use dict to store unique tenant info
    subscriptions_ids = []
    subscription_names = []

    for sub in subscription_client.subscriptions.list():
        if sub.state == 'Enabled':
            tenant_id = sub.tenant_id
            subscriptions_ids.append(sub.id[15:])
            subscription_names.append(sub.display_name)
            if tenant_id not in tenants_dict:
                tenants_dict[tenant_id] = None

    # Getting tenant names
    for tenant in subscription_client.tenants.list():
        if tenant.id[9:] in tenants_dict:
            tenants_dict[tenant.id[9:]] = tenant.display_name

    # Create lists in the same order as subscriptions
    tenants_ids = []
    tenants_names = []
    for sub in subscription_client.subscriptions.list():
        if sub.state == 'Enabled':
            tenants_ids.append(sub.tenant_id)
            tenants_names.append(tenants_dict.get(sub.tenant_id, "Unknown Tenant"))

    return tenants_ids, tenants_names, subscriptions_ids, subscription_names

def iterator_wrapper(iterator):
    flag_httpresponse_code_429 = False
    while True:
        try:
            iterator,iterator_copy = itertools.tee(iterator)
            iterator_value = next(iterator)
            yield (iterator_value,None)
            flag_httpresponse_code_429 = False
        except StopIteration as e_stop:
            yield (None,e_stop)
        except azure.core.exceptions.HttpResponseError as e_http:
            if e_http.status_code == 429:
               wait_time = int(e_http.response.headers["Retry-After"]) + 10
               print("[!] Encounter throttling limits error. In order to continue the scan, you need to wait {} min".format(wait_time) ,flush=True)
               response = pyip.inputMenu(['N', 'Y'],"Do you wish to wait {} min ? or stop the scan here and recieve the script outcome till this part\nEnter Y for Yes, Continue the scan\nEnter N for No, Stop the scan \n".format(wait_time))              
             
               if response == 'Y':
                   print("[!] {} min timer started".format(wait_time), flush=True)
                   time.sleep(wait_time)
               else:
                   yield (STOP_SCAN_FLAG, None)
           
               if flag_httpresponse_code_429:
                   # This means this current iterable object got throttling limit 2 times in a row, this condition has been added in order to prevent an infinite loop of throttling limit.
                   print("[!] The current object we have been trying to access has triggered throttling limit error 2 times in a row, skipping this object ", flush=True)
                   flag_httpresponse_code_429 = False
                   yield (None,e_http)
               else:
                   flag_httpresponse_code_429 = True
                   iterator = iterator_copy
                   continue
                
            else:
                yield (None,e_http)
        except Exception as e:
            yield (None,e)      


def check_storage_account(account_name, key):
    blob_service_client = BlobServiceClient(ENDPOINT_URL.format(account_name), credential=key)
    containers = blob_service_client.list_containers(timeout=15)
    public_containers = list() 

    for cont,e in iterator_wrapper(containers):
        if cont == STOP_SCAN_FLAG:
            break
        if e :
            if type(e) is not StopIteration:   
                print("\t\t[-] Could not scan the container of the account{} due to the error{}. skipping".format(account_name,e), flush=True) 
                continue
            else:
                break
        if cont.public_access is not None:
            public_containers.append(cont)

    return public_containers


def check_subscription(tenant_id, tenant_name, sub_id, sub_name, creds):
    print("\n\t[*] Checking subscription {}:".format(sub_name), flush=True)

    storage_client = StorageManagementClient(creds, sub_id)

    # Obtain the management object for resources
    resource_client = ResourceManagementClient(creds, sub_id)

    # Retrieve the list of resource groups
    group_list = resource_client.resource_groups.list()
    resource_groups = [group.name for group in list(group_list)]
    print("\t\t[+] Found {} resource groups".format(len(resource_groups)), flush=True)
    group_to_names_dict = {group: dict() for group in resource_groups}

    accounts_counter = 0
    for group in resource_groups:
        for item,e in iterator_wrapper(storage_client.storage_accounts.list_by_resource_group(group)):
            if item == STOP_SCAN_FLAG:
               break
            if e :
                if type(e) is not StopIteration:   
                    print("\t\t[-] Could not access one of the resources of the group {} ,due to the error {} skipping the resource".format(group,e), flush=True) 
                    continue
                else:
                    break
            accounts_counter += 1
            group_to_names_dict[group][item.name] = ''

    print("\t\t[+] Found {} storage accounts".format(accounts_counter), flush=True)

    for group in resource_groups:
        for account in group_to_names_dict[group].keys():
            try:
                storage_keys = storage_client.storage_accounts.list_keys(group, account)
                storage_keys = {v.key_name: v.value for v in storage_keys.keys}
                group_to_names_dict[group][account] = storage_keys['key1']
            except azure.core.exceptions.HttpResponseError as e:
                print("\t\t[-] User do not have permissions to retrieve storage accounts keys in the given"
                      " subscription", flush=True)
                print("\t\t    Can not scan storage accounts", flush=True)
                return
                

    output_list = list()

    for group in resource_groups:
        for account in group_to_names_dict[group].keys():
            key = group_to_names_dict[group][account]
            public_containers = check_storage_account(account, key)

            for cont in public_containers:
                access_level = cont.public_access
                container_client = ContainerClient(ENDPOINT_URL.format(account), cont.name, credential=key)
                files = [f.name for f in container_client.list_blobs()]
                ext_dict = count_files_extensions(files, EXTENSIONS)
                row = [tenant_id, tenant_name, sub_id, sub_name, group, account, cont.name, access_level,
                       CONTAINER_URL.format(account, cont.name), len(files)]

                for ext in ext_dict.keys():
                    row.append(ext_dict[ext])

                output_list.append(row)

    print("\t\t[+] Scanned all storage accounts successfully", flush=True)

    if len(output_list) > 0:
        print("\t\t[+] Found {} PUBLIC containers".format(len(output_list)), flush=True)
    else:
        print("\t\t[+] No PUBLIC containers found")

    header = ["Tenant ID", "Tenant Name", "Subscription ID", "Subscription Name", "Resource Group", "Storage Account", "Container",
              "Public Access Level", "URL", "Total Files"]

    for ext in EXTENSIONS:
        header.append(ext)

    header.append("others")
    write_csv('public-containers-{}.csv'.format(date.today()), header, output_list)


def delete_csv():
    for file in os.listdir("."):
        if os.path.isfile(file) and file.startswith("public"):
            os.remove(file)


def write_csv(file_name, header, rows):
    file_exists = os.path.isfile(file_name)

    with open(file_name, 'a', newline='', encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(header)

        for r in rows:
            writer.writerow(r)


def count_files_extensions(files, extensions):
    counter_dict = dict()
    others_cnt = 0

    for extension in extensions:
        counter_dict[extension] = 0

    for f_name in files:
        in_extensions = False

        for extension in extensions:
            if f_name.endswith(extension):
                in_extensions = True
                counter_dict[extension] += 1
                break

        if not in_extensions:
            if f_name.endswith("doc"):
                counter_dict['docx'] += 1
            elif f_name.endswith("xls"):
                counter_dict['xlsx'] += 1
            else:
                others_cnt += 1

    counter_dict['other'] = others_cnt
    return counter_dict

def choose_subscriptions(credentials):
    tenants_ids, tenants_names, subs_ids, subs_names = get_tenants_and_subscriptions(credentials)
    print("[+] Found {} subscriptions".format(len(subs_ids)), flush=True)
    response = pyip.inputMenu(['N', 'Y'],"Do you wish to run the script on all the subscriptions?\nEnter Y for all subscriptions\nEnter N to choose for specific subscriptions\n")
    if response == 'Y':
        return tenants_ids, tenants_names, subs_ids, subs_names
    else:
        response_sub = pyip.inputMenu(subs_names,"Enter the specific subscriptions you wish to test\n")
        subs_index = subs_names.index(response_sub)
        return tenants_ids[subs_index], tenants_names[subs_index], subs_ids[subs_index], subs_names[subs_index]
   


def print_logo():
    logo = r"""
-------------------------------------------------------------    
    
    ______ _       _     _   _             _            
    | ___ \ |     | |   | | | |           | |           
    | |_/ / | ___ | |__ | |_| |_   _ _ __ | |_ ___ _ __ 
    | ___ \ |/ _ \| '_ \|  _  | | | | '_ \| __/ _ \ '__|
    | |_/ / | (_) | |_) | | | | |_| | | | | ||  __/ |   
    \____/|_|\___/|_.__/\_| |_/\__,_|_| |_|\__\___|_|
                                                                  
-------------------------------------------------------------  
                    Author: Daniel Niv
                    Modified by: Johnny Monteleone
------------------------------------------------------------- 
                                       
    """
    print(logo, flush=True)


def main():
    print_logo()
    
    if not setup_azure_cli_path():
        print("[-] Could not find Azure CLI installation. Please install Azure CLI first.", flush=True)
        return
        
    credentials = get_credentials()
    delete_csv()

    if credentials is None:
        print("[-] Unable to login to a valid Azure user", flush=True)
        return

    tenants_ids, tenants_names, subs_ids, subs_names = choose_subscriptions(credentials)

    if isinstance(tenants_ids, list):
        for i in range(len(subs_ids)):
            check_subscription(tenants_ids[i], tenants_names[i], subs_ids[i], subs_names[i], credentials)
    else:
        check_subscription(tenants_ids, tenants_names, subs_ids, subs_names, credentials)

    print("\n[+] Scanned all subscriptions successfully", flush=True)
    print("[+] Check out public-containers-{}.csv file for a fully detailed report".format(date.today()), flush=True)


if __name__ == '__main__':
    main()
