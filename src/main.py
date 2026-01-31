import logging
import pandas as pd
import os
from datetime import datetime
from io import StringIO
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
load_dotenv()
from scraping.otomoto_client import OtomotoClient
from scraping.link_extractor import LinkExtractor
from scraping.offer_parser import OfferParser

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Azure configuration
# In Docker, it will get it from environment variables, locally you can hardcode it for testing,
# or set it in a .env file.
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "raw-data"

def save_batch_to_azure(dataset, batch_number):
    """
    Sends a list of dictionaries (dataset) as a CSV file to Azure Blob Storage.
    """
    if not dataset:
        return

    # Create a DataFrame
    df = pd.DataFrame(dataset)
    
    # Generate a filename: e.g., dump_20240117_batch_1.csv
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dump_{timestamp}_batch_{batch_number}.csv"

    # ENG: Convert to CSV in memory (string buffer) - to avoid disk write
    output = StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    data_to_upload = output.getvalue().encode('utf-8-sig')

    if AZURE_CONNECTION_STRING:
        try:
            blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=filename)
            
            blob_client.upload_blob(data_to_upload, overwrite=True)
            logging.info(f"Batch {batch_number} ({len(df)} cars) uploaded to Azure: {filename}")
        except Exception as e:
            logging.error(f"Error uploading to Azure: {e}")
            # Fallback to local save
            _save_local_backup(df, filename)
    else:
        logging.error("AZURE_STORAGE_CONNECTION_STRING not found. Saving locally.")
        _save_local_backup(df, filename)

def _save_local_backup(df, filename):
    os.makedirs("data_backup", exist_ok=True)
    path = os.path.join("data_backup", filename)
    df.to_csv(path, index=False, encoding='utf-8-sig')
    logging.info(f"Saved local copy: {path}")

def main():
    logging.info("Starting ETL process with Cloud Upload...")
    
    client = OtomotoClient()
    extractor = LinkExtractor(client)
    
    # Here you set how many pages to fetch.
    # If you want all available pages, set num_pages=None
    links = extractor.get_links(start_page=1, num_pages=None) 
    
    logging.info(f"🔗 Extracted {len(links)} links. Starting processing...")
    
    parser = OfferParser(client)
    
    batch_data = []
    BATCH_SIZE = 50 # Number of offers per batch upload
    batch_counter = 1
    
    for i, link in enumerate(links):
        logging.info(f"Parsing {i+1}/{len(links)}")
        try:
            data = parser.parse_offer(link)
            if data:
                batch_data.append(data)
        except Exception as e:
            logging.error(f"Error parsing {link}: {e}")
            
        if len(batch_data) >= BATCH_SIZE:
            save_batch_to_azure(batch_data, batch_counter)
            batch_data = []
            batch_counter += 1

    if batch_data:
        save_batch_to_azure(batch_data, batch_counter)

    logging.info("Processing finished.")

if __name__ == "__main__":
    main()