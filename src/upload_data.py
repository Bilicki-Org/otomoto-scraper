from azure.ai.ml.entities import Data
from azure.ai.ml.constants import AssetTypes
from connect_utils import get_ml_client

def upload_data_to_azure(file_path: str, data_name: str, version: str) -> None:
    try:
        # Connect to Azure ML
        ml_client = get_ml_client()
        print(f"Connecting with: {ml_client.workspace_name}")

        my_data = Data(
            path=file_path,
            type=AssetTypes.URI_FILE,
            description="Test Dataset",
            name=data_name,
            version=version
        )

        # 3. Send data to Azure ML
        print(f"Sending '{data_name}' (v{version}) to the cloud...")
        ml_client.data.create_or_update(my_data)
        print("Sending completed!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    upload_data_to_azure(
        file_path="./data/otomoto_cars_test.csv", 
        data_name="otomoto-cars-raw", 
        version="1"
    )