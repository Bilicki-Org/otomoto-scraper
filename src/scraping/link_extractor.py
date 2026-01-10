import logging
from typing import List
from bs4 import BeautifulSoup
from .otomoto_client import OtomotoClient

class LinkExtractor:
    """
    Responsible for iterating over search results pages and extracting offer URLs.
    """

    def __init__(self, client: OtomotoClient):
        self.client = client
        # Base URL for passenger cars
        self.base_url = "https://www.otomoto.pl/osobowe"

    def _extract_links_from_html(self, html_content: str) -> List[str]:
        """Parses HTML and finds links to specific offers."""
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []
        
        # Strategy: Look for all <a> tags containing '/oferta/' in href
        # This is more robust than relying on specific CSS classes which change often.
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if "otomoto.pl/osobowe/oferta/" in href:
                # Clean up URL (remove hashtags or query params if needed)
                links.append(href.split('#')[0])
                
        # Remove duplicates
        return list(set(links))

    def get_links(self, start_page: int = 1, num_pages: int = 1) -> List[str]:
        all_links = []
        empty_page_count = 0  # Licznik pustych stron pod rząd
        
        for i in range(num_pages):
            current_page = start_page + i
            url = f"{self.base_url}?search%5Border%5D=created_at_first%3Adesc&page={current_page}"
            
            logging.info(f"Scraping links from page {current_page}...")
            response = self.client.get(url)
            
            if response:
                page_links = self._extract_links_from_html(response.text)
                
                # --- LOGIKA WCZESNEGO ZATRZYMANIA ---
                if not page_links:
                    logging.warning(f"No links found on page {current_page}.")
                    empty_page_count += 1
                    if empty_page_count >= 3:  # Jeśli 3 strony pod rząd są puste -> KONIEC
                        logging.info("Three consecutive empty pages. Stopping pagination.")
                        break
                else:
                    empty_page_count = 0  # Resetujemy licznik, jeśli coś znaleźliśmy
                    logging.info(f"Found {len(page_links)} links on page {current_page}.")
                    all_links.extend(page_links)
            else:
                logging.warning(f"Skipping page {current_page} due to connection error.")
                
        return list(set(all_links))