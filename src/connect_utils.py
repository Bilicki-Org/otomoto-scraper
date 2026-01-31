import os
from dotenv import load_dotenv
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

# Load environment variables from .env file (only for local development)
load_dotenv()

def get_ml_client() -> MLClient:
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    resource_group = os.getenv("AZURE_RESOURCE_GROUP")
    workspace_name = os.getenv("AZURE_WORKSPACE_NAME")

    # Validation if variables exist
    if not all([subscription_id, resource_group, workspace_name]):
        raise ValueError("Lack of environment variables to configure Azure!")

    credential = DefaultAzureCredential()
    
    ml_client = MLClient(
        credential=credential,
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )
    
    return ml_client

def main() -> None:
    """Main function testing the connection."""
    print("Trying to connect to Azure ML...")
    
    try:
        client = get_ml_client()
        # Simple check operation - get the workspace name from the cloud
        ws = client.workspaces.get(client.workspace_name)
        print(f"Success! Connected to Workspace: {ws.name}")
        print(f"Location: {ws.location}")
        print(f"Description: {ws.description}")
        
    except Exception as e:
        print(f"Error connecting: {e}")
        print("Hint: Did you create a Workspace in the Azure portal and enter the data in .env?")

if __name__ == "__main__":
    main()