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

# Konfiguracja Azure
# W Dockerze pobierze to ze zmiennych środowiskowych, lokalnie możesz wpisać "na sztywno" do testów,
# ale bezpieczniej jest ustawić to w systemie.
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "raw-data"

def save_batch_to_azure(dataset, batch_number):
    """
    Wysyła listę słowników (dataset) jako plik CSV do Azure Blob Storage.
    """
    if not dataset:
        return

    # Tworzymy DataFrame
    df = pd.DataFrame(dataset)
    
    # Generujemy nazwę pliku: np. dump_20240117_batch_1.csv
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dump_{timestamp}_batch_{batch_number}.csv"

    # Konwersja do CSV w pamięci (string buffer) - żeby nie zapisywać na dysku
    output = StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig') # <-- PAMIĘTAJ O UTF-8-SIG
    data_to_upload = output.getvalue().encode('utf-8-sig')

    if AZURE_CONNECTION_STRING:
        try:
            blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=filename)
            
            blob_client.upload_blob(data_to_upload, overwrite=True)
            logging.info(f"✅ Paczka {batch_number} ({len(df)} aut) wysłana do Azure: {filename}")
        except Exception as e:
            logging.error(f"❌ Błąd wysyłania do Azure: {e}")
            # Awaryjny zapis lokalny
            _save_local_backup(df, filename)
    else:
        logging.warning("⚠️ Brak AZURE_STORAGE_CONNECTION_STRING. Zapisuję lokalnie.")
        _save_local_backup(df, filename)

def _save_local_backup(df, filename):
    os.makedirs("data_backup", exist_ok=True)
    path = os.path.join("data_backup", filename)
    df.to_csv(path, index=False, encoding='utf-8-sig')
    logging.info(f"💾 Zapisano lokalną kopię: {path}")

def main():
    logging.info("🚀 Starting ETL process with Cloud Upload...")
    
    client = OtomotoClient()
    extractor = LinkExtractor(client)
    
    # UWAGA: Tu ustawiasz ile stron chcesz pobrać.
    # Jeśli chcesz wszystko, musisz zmienić logikę w LinkExtractor, żeby szedł do końca.
    # Na razie testowo np. 5 stron.
    links = extractor.get_links(start_page=1, num_pages=5) 
    
    logging.info(f"🔗 Extracted {len(links)} links. Starting processing...")
    
    parser = OfferParser(client)
    
    batch_data = []
    BATCH_SIZE = 50 # Co ile aut wysyłamy do chmury?
    batch_counter = 1
    
    for i, link in enumerate(links):
        logging.info(f"Parsing {i+1}/{len(links)}")
        try:
            data = parser.parse_offer(link)
            if data:
                batch_data.append(data)
        except Exception as e:
            logging.error(f"Błąd przy parsowaniu {link}: {e}")
            
        # Sprawdzamy, czy czas na wysyłkę paczki
        if len(batch_data) >= BATCH_SIZE:
            save_batch_to_azure(batch_data, batch_counter)
            batch_data = [] # Czyścimy listę, zwalniamy pamięć
            batch_counter += 1

    # Na koniec wysyłamy to, co zostało (resztki)
    if batch_data:
        save_batch_to_azure(batch_data, batch_counter)

    logging.info("🏁 Processing finished.")

if __name__ == "__main__":
    main()