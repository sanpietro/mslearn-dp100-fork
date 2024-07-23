import sys
import random
import string
import subprocess
from azure.identity import DefaultAzureCredential
from azureml.core import Workspace, ComputeTarget, Datastore, Dataset
from azureml.core.compute import ComputeInstance, AmlCompute
from azureml.core.compute_target import ComputeTargetException
from azureml.data.data_reference import DataReference
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource import SubscriptionClient

def create_random_suffix(length=6):
    """ Generate a random string of letters and digits """
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def register_resource_provider(credential, subscription_id):
    """ Register an Azure resource provider """
    client = ResourceManagementClient(credential, subscription_id)
    # Register the machine learning resource provider
    provider = client.providers.register('Microsoft.MachineLearningServices')
    print(f"Registered resource provider: {provider.namespace}")

def run_cli_command(command):
    """ Run Azure CLI command """
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        print(result.stdout)
    except subprocess.CalledProcessError as error:
        print("CLI Command failed:", error)
        print(error.output)

def create_aml_workspace():
    credential = DefaultAzureCredential()

    # Get the subscription ID
    subscription_client = SubscriptionClient(credential)
    subscription_id = next(subscription_client.subscriptions.list()).subscription_id

    # Register resource providers
    register_resource_provider(credential, subscription_id)

    # Generate unique names for the resource group and workspace
    suffix = create_random_suffix()
    resource_group = f"aml_rg_{suffix}"
    workspace_name = f"aml_ws_{suffix}"

    # Input region
    location = input("Choose from the following list of regions: 'eastus', 'westus', 'centralus', 'northeurope', 'westeurope': ")

    # Print the chosen location
    print(f"You have chosen the region: {location}")


    try:
        # Create the resource group and workspace
        print(f"Creating resource group '{resource_group}' and workspace '{workspace_name}' in {location}")
        ws = Workspace.create(name=workspace_name,
                              subscription_id=subscription_id,
                              resource_group=resource_group,
                              create_resource_group=True,
                              location=location,
                              exist_ok=True)

        print("Workspace created successfully.")
    except Exception as e:
        print(f"Failed to create workspace: {e}")
        return 1

    # Compute instance creation
    compute_instance_name = f"ci-{suffix}"
    compute_config = ComputeInstance.provisioning_configuration(vm_size='STANDARD_DS11_V2')

    try:
        compute_instance = ComputeInstance.create(ws, compute_instance_name, compute_config)
        compute_instance.wait_for_completion(show_output=True)
        print(f"CI '{compute_instance_name}' created successfully.")
    except Exception as e:
        print(f"Failed to create compute instance: {e}")

    # Compute cluster creation
    compute_cluster_name = "aml-cluster"
    compute_config = AmlCompute.provisioning_configuration(vm_size="STANDARD_DS11_V2", max_nodes=2)
    try:
        compute_cluster = ComputeTarget.create(ws, compute_cluster_name, compute_config)
        compute_cluster.wait_for_completion(show_output=True)
        print(f"Training '{compute_cluster_name}' created successfully.")
    except ComputeTargetException as e:
        print(f"Failed to create compute cluster: {e}")
    try:
        compute_config = AmlCompute.provisioning_configuration(vm_size="STANDARD_DS11_V2", max_nodes=2)
        compute_cluster = ComputeTarget.create(ws, compute_cluster_name, compute_config)
        compute_cluster.wait_for_completion(show_output=True)
        print(f"Compute cluster '{compute_cluster_name}' created successfully.")
    except ComputeTargetException as e:
        print(f"Failed to create compute cluster: {e}")

    run_cli_command(f'az ml data create --type uri_file --name "diabetes-data" --path ./data/diabetes.csv --workspace-name {workspace_name} --resource-group {resource_group}')
    

if __name__ == '__main__':
    sys.exit(create_aml_workspace())
