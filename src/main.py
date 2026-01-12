import logging
import pandas as pd
import os
from scraping.otomoto_client import OtomotoClient
from scraping.link_extractor import LinkExtractor
from scraping.offer_parser import OfferParser

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    logging.info("🚀 Starting ETL process...")
    
    client = OtomotoClient()
    extractor = LinkExtractor(client)
    
    # KROK 1: Pobieranie linków
    # Ustawiamy 2 strony = ok. 64 ogłoszenia. Idealne do testów.
    links = extractor.get_links(start_page=1, num_pages=1)
    
    logging.info(f"🔗 Successfully extracted {len(links)} links.")
    
    # KROK 2: Pobieranie szczegółów
    parser = OfferParser(client)
    dataset = []
    
    # Pętla po linkach
    for i, link in enumerate(links):
        logging.info(f"Parsing {i+1}/{len(links)}: {link}")
        try:
            data = parser.parse_offer(link)
            if data:
                dataset.append(data)
        except Exception as e:
            logging.error(f"Błąd przy parsowaniu {link}: {e}")
            
    # KROK 3: Zapis danych
    if dataset:
        output_dir = "data"
        os.makedirs(output_dir, exist_ok=True)
        
        # To jest plik, którego Ci brakowało:
        output_file = os.path.join(output_dir, "cars_dataset_100.csv")
        
        df = pd.DataFrame(dataset)
        df.to_csv(output_file, index=False)
        logging.info(f"✅ Data saved to {output_file}. Total records: {len(df)}")
    else:
        logging.warning("⚠️ No data extracted.")

if __name__ == "__main__":
    main()