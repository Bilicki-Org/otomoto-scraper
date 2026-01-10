import logging
import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class OtomotoClient:
    """
    Wrapper for requests.Session to handle headers, retries, and delays.
    Mimics a real browser to avoid anti-bot detection.
    """

    def __init__(self):
        self.session = requests.Session()
        
        # Standard headers to look like a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/',
        })

        # Retry strategy: 3 retries, exponential backoff
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def get(self, url: str) -> requests.Response:
        """
        Executes a GET request with random sleep to respect rate limits.
        
        Args:
            url (str): The URL to fetch.
            
        Returns:
            requests.Response: The response object or None if failed.
        """
        try:
            # Random delay between 1 and 3 seconds (Crucial for scraping!)
            sleep_time = random.uniform(1.0, 3.0)
            time.sleep(sleep_time)

            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None