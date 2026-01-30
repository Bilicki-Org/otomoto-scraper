import logging
from typing import List, Optional
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
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if "otomoto.pl/osobowe/oferta/" in href:
                # Clean up URL (remove hashtags or query params if needed)
                links.append(href.split('#')[0])
                
        # Remove duplicates
        return list(set(links))

    def get_links(self, start_page: int = 1, num_pages: Optional[int] = None) -> List[str]:
        """
        Pobiera linki. 
        Jeśli num_pages jest podane (np. 5), pobierze 5 stron.
        Jeśli num_pages is None, pobiera aż Otomoto przestanie zwracać wyniki.
        """
        all_links = []
        current_page = start_page
        empty_page_count = 0  # Licznik pustych stron pod rząd
        pages_processed = 0   # Licznik przetworzonych stron

        while True:
            # 1. Sprawdzenie limitu stron (jeśli został ustawiony przez użytkownika)
            if num_pages is not None and pages_processed >= num_pages:
                logging.info(f"Osiągnięto limit {num_pages} stron. Kończę pobieranie.")
                break

            url = f"{self.base_url}?search%5Border%5D=created_at_first%3Adesc&page={current_page}"
            
            logging.info(f"Scraping links from page {current_page}...")
            response = self.client.get(url)
            
            if response:
                page_links = self._extract_links_from_html(response.text)
                
                # --- LOGIKA WCZESNEGO ZATRZYMANIA ---
                if not page_links:
                    logging.warning(f"No links found on page {current_page}.")
                    empty_page_count += 1
                    # Jeśli 3 strony pod rząd są puste -> KONIEC (nawet jeśli num_pages=None)
                    if empty_page_count >= 3: 
                        logging.info("Three consecutive empty pages. Stopping pagination.")
                        break
                else:
                    empty_page_count = 0  # Resetujemy licznik, jeśli coś znaleźliśmy
                    logging.info(f"Found {len(page_links)} links on page {current_page}.")
                    all_links.extend(page_links)
            else:
                logging.warning(f"Skipping page {current_page} due to connection error.")
                
            # Przechodzimy do kolejnej strony
            current_page += 1
            pages_processed += 1
                
        return list(set(all_links))