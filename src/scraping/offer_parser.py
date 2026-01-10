import logging
import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from .otomoto_client import OtomotoClient

class OfferParser:
    """
    Extracts detailed attributes from a single offer page.
    Hybrid approach:
    - Price: Uses CSS classes (optimized for current HTML).
    - Location: Uses 'Znajdź na mapie' text search (proven legacy method).
    - Tech Specs: Uses data-testid attributes.
    """

    def __init__(self, client: OtomotoClient):
        self.client = client

    def _clean_numeric(self, value: Any) -> Optional[float]:
        """Converts strings like '150 000 km' or '93 800' to pure numbers."""
        if not value: return None
        try:
            # Remove spaces, non-breaking spaces, and letters
            clean_str = re.sub(r'[^\d.,]', '', str(value)).replace(',', '.')
            if not clean_str: return None
            return float(clean_str)
        except ValueError:
            return None

    def _parse_bool(self, value: Any) -> str:
        """Standardizes boolean fields."""
        if not value: return "No"
        val_str = str(value).lower().strip()
        if val_str in ['tak', 'yes', 'true', '1']: return "Yes"
        return "No"

    def _extract_price_html(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extracts price using specific CSS classes.
        """
        price_data = {"price": None, "currency": None}
        try:
            # 1. Price Value
            number_span = soup.find('span', class_='offer-price__number')
            if number_span:
                price_data['price'] = self._clean_numeric(number_span.get_text(strip=True))

            # 2. Currency
            currency_span = soup.find('span', class_=lambda x: x and 'offer-price__currency' in x)
            if currency_span:
                price_data['currency'] = currency_span.get_text(strip=True)
            elif price_data['price']:
                price_data['currency'] = "PLN" 
        except Exception as e:
            logging.warning(f"Price extraction failed: {e}")
        return price_data

    def _extract_location_html(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extracts location searching for 'Znajdź na mapie'.
        Clean logic: Strips Zip Codes AND 'Polska -' prefixes.
        """
        loc_data = {"location_city": None, "location_district": None, "location_voivodeship": None}
        
        # Helper function to clean text garbage
        def clean_name(text: Optional[str]) -> Optional[str]:
            if not text: return None
            # 1. Usuń kody pocztowe (XX-XXX)
            text = re.sub(r'\d{2}-\d{3}', '', text)
            # 2. Usuń "Polska" oraz opcjonalne myślniki/spacje po lub przed (np. "Polska - ")
            text = re.sub(r'Polska\s*[-–]?\s*', '', text, flags=re.IGNORECASE)
            # 3. Usuń nawiasy np. (Polska)
            text = text.replace('(Polska)', '').replace('()', '')
            # 4. Usuń znaki interpunkcyjne z początku i końca (przecinki, myślniki, spacje)
            text = re.sub(r'^[\W_]+|[\W_]+$', '', text).strip()
            
            return text if text else None

        try:
            map_header = soup.find('p', string=re.compile('Znajdź na mapie'))
            
            location_tag = None
            if map_header:
                parent_div = map_header.find_parent('div')
                if parent_div:
                    link_tag = parent_div.find('a')
                    if link_tag:
                        location_tag = link_tag
                    else:
                        paragraphs = parent_div.find_all('p')
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if "Znajdź na mapie" not in text and len(text) > 3:
                                location_tag = p
                                break

            if location_tag:
                full_text = location_tag.get_text(strip=True)
                
                # --- STRATEGIA 1: KOD POCZTOWY JAKO KOTWICA ---
                zip_match = re.search(r'(\d{2}-\d{3})\s+([^,]+)', full_text)
                parts = [p.strip() for p in full_text.split(',') if p.strip()]
                
                if zip_match:
                    city_raw = zip_match.group(2).strip()
                    clean_city = clean_name(city_raw)
                    
                    loc_data['location_city'] = clean_city
                    loc_data['location_district'] = clean_city # Domyślny powiat = miasto
                    
                    if len(parts) >= 1:
                        loc_data['location_voivodeship'] = clean_name(parts[-1])
                    
                    if len(parts) >= 3:
                        potential_district = clean_name(parts[-2])
                        # Zabezpieczenie przed nadpisaniem powiatu nazwą miasta, jeśli są identyczne
                        if potential_district and clean_city and potential_district.lower() != clean_city.lower():
                             loc_data['location_district'] = potential_district

                # --- STRATEGIA 2: BRAK KODU POCZTOWEGO ---
                else:
                    if len(parts) >= 1:
                        loc_data['location_voivodeship'] = clean_name(parts[-1])
                    
                    if len(parts) >= 3:
                        loc_data['location_city'] = clean_name(parts[0])
                        loc_data['location_district'] = clean_name(parts[1])
                    elif len(parts) == 2:
                        cleaned = clean_name(parts[0])
                        loc_data['location_city'] = cleaned
                        loc_data['location_district'] = cleaned
                    elif len(parts) == 1:
                        cleaned = clean_name(parts[0])
                        loc_data['location_city'] = cleaned

        except Exception as e:
            logging.warning(f"Location extraction error: {e}")
            
        return loc_data

    def _extract_tech_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extracts technical parameters using data-testid attributes.
        """
        data = {}
        testid_map = {
            'year': 'year', 'mileage_km': 'mileage', 'engine_capacity_cm3': 'engine_capacity',
            'fuel_type': 'fuel_type', 'power_hp': 'engine_power', 'gearbox': 'gearbox',
            'drive': 'transmission', 'body_type': 'body_type', 'doors': 'door_count',
            'seats': 'nr_seats', 'color': 'color', 'origin': 'country_origin',
            'brand': 'make', 'model': 'model', 'generation': 'generation',
            'version': 'version', 'accident_free': 'no_accident', 'damaged': 'damaged',
            'first_owner': 'original_owner', 'registered_pl': 'registered',
            'has_registration': 'has_registration', 'condition': 'new_used'
        }

        for my_key, testid in testid_map.items():
            div = soup.find('div', {'data-testid': testid})
            if div:
                # Value is typically in the 2nd paragraph or last child
                paragraphs = div.find_all('p')
                if len(paragraphs) >= 2:
                    data[my_key] = paragraphs[1].get_text(strip=True)
                elif len(paragraphs) == 1:
                    data[my_key] = paragraphs[0].get_text(strip=True)
                else:
                    data[my_key] = div.get_text(strip=True)
        return data

    def parse_offer(self, url: str) -> Optional[Dict[str, Any]]:
        logging.info(f"Processing offer: {url}")
        response = self.client.get(url)
        if not response: return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Base Info
        desc_div = soup.find('div', {'data-testid': 'textWrapper'})
        description = desc_div.get_text(separator='\n', strip=True) if desc_div else ""
        
        title_tag = soup.find('h1', class_='offer-title') or soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        # 2. Extract Components
        price_info = self._extract_price_html(soup)
        loc_info = self._extract_location_html(soup) # Restored Logic
        tech_data = self._extract_tech_data(soup)

        # 3. Assemble
        offer_data = {
            "link": url,
            "title": title,
            "description": description,
            **price_info,
            **loc_info,
        }

        # 4. Merge Tech Data
        for key, value in tech_data.items():
            if key in ["year", "mileage_km", "engine_capacity_cm3", "power_hp", "doors", "seats"]:
                offer_data[key] = self._clean_numeric(value)
            elif key in ["accident_free", "damaged", "first_owner", "registered_pl", "has_registration"]:
                offer_data[key] = self._parse_bool(value)
            else:
                offer_data[key] = value

        return offer_data