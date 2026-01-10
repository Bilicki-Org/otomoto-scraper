import logging
import pandas as pd
import os
from scraping.otomoto_client import OtomotoClient
from scraping.link_extractor import LinkExtractor
from scraping.offer_parser import OfferParser

# Configure logging to show timestamps
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """
    Main execution pipeline:
    1. Setup Client
    2. Extract Links (Batch)
    3. Parse Details (One by one)
    4. Save to CSV
    """
    logging.info("Starting ETL process...")
    
    # 1. Initialize the client (Browser session)
    client = OtomotoClient()
    
    # 2. Extract Links
    # In a real scenario, you might want to load links from a file if they are already scraped.
    extractor = LinkExtractor(client)
    # Let's scrape just 1 page for testing purposes
    links = extractor.get_links(start_page=1, num_pages=4)
    
    logging.info(f"Successfully extracted {len(links)} links.")
    
    # 3. Parse Details
    parser = OfferParser(client)
    dataset = []
    
    for i, link in enumerate(links):
        logging.info(f"Parsing {i+1}/{len(links)}...")
        data = parser.parse_offer(link)
        if data:
            dataset.append(data)
            
    # 4. Save Data
    if dataset:
        output_dir = "data"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "cars_dataset.csv")
        
        df = pd.DataFrame(dataset)
        df.to_csv(output_file, index=False)
        logging.info(f"Data saved to {output_file}. Total records: {len(df)}")
    else:
        logging.warning("No data extracted.")

if __name__ == "__main__":
    main()