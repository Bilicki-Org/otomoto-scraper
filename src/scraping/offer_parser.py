import logging
import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from .otomoto_client import OtomotoClient

class OfferParser:
    """
    Extracts raw attributes from a single offer page.
    Cleaned version: NO AI here. Just raw data extraction.
    """

    def __init__(self, client: OtomotoClient):
        self.client = client
        # USUNIĘTO: self.llm = LLMAnalyzer() 
        # Scraper ma być lekki!

    def _clean_numeric(self, value: Any) -> Optional[float]:
        if not value: return None
        try:
            clean_str = re.sub(r'[^\d.,]', '', str(value)).replace(',', '.')
            if not clean_str: return None
            return float(clean_str)
        except ValueError:
            return None

    def _parse_bool(self, value: Any) -> str:
        if not value: return "No"
        val_str = str(value).lower().strip()
        if val_str in ['tak', 'yes', 'true', '1']: return "Yes"
        return "No"

    def _extract_price_html(self, soup: BeautifulSoup) -> Dict[str, Any]:
        price_data = {"price": None, "currency": None}
        try:
            number_span = soup.find('span', class_='offer-price__number')
            if number_span:
                price_data['price'] = self._clean_numeric(number_span.get_text(strip=True))
            
            currency_span = soup.find('span', class_=lambda x: x and 'offer-price__currency' in x)
            if currency_span:
                price_data['currency'] = currency_span.get_text(strip=True)
            elif price_data['price']:
                price_data['currency'] = "PLN" 
        except Exception:
            pass # Ignorujemy błędy ceny, zostaną None
        return price_data

    def _extract_location_html(self, soup: BeautifulSoup) -> Dict[str, str]:
        loc_data = {"location_city": None, "location_district": None, "location_voivodeship": None}
        
        MAJOR_CITIES_MAP = {
            "warszawa": "Mazowieckie", "kraków": "Małopolskie", "łódź": "Łódzkie",
            "wrocław": "Dolnośląskie", "poznań": "Wielkopolskie", "gdańsk": "Pomorskie",
            "szczecin": "Zachodniopomorskie", "bydgoszcz": "Kujawsko-pomorskie",
            "lublin": "Lubelskie", "katowice": "Śląskie", "białystok": "Podlaskie",
            "gdynia": "Pomorskie", "częstochowa": "Śląskie", "radom": "Mazowieckie",
            "sosnowiec": "Śląskie", "toruń": "Kujawsko-pomorskie", "kielce": "Świętokrzyskie",
            "rzeszów": "Podkarpackie", "gliwice": "Śląskie", "zabrze": "Śląskie",
            "olsztyn": "Warmińsko-mazurskie", "bielsko-biała": "Śląskie", "bytom": "Śląskie",
            "zielona góra": "Lubuskie", "rybnik": "Śląskie", "ruda śląska": "Śląskie",
            "opole": "Opolskie", "tychy": "Śląskie", "gorzów wielkopolski": "Lubuskie",
            "elbląg": "Warmińsko-mazurskie", "płock": "Mazowieckie", "sopot": "Pomorskie",
            "wałbrzych": "Dolnośląskie", "tarnów": "Małopolskie", "chorzów": "Śląskie",
            "kalisz": "Wielkopolskie", "koszalin": "Zachodniopomorskie", "legnica": "Dolnośląskie",
        }

        def clean_name(text: Optional[str]) -> Optional[str]:
            if not text: return None
            text = re.sub(r'\d{2}[-\s]\d{3}', '', text)
            text = re.sub(r'Polska\s*[-–]?\s*', '', text, flags=re.IGNORECASE)
            text = re.sub(r'^gm\.\s*', '', text, flags=re.IGNORECASE)
            text = text.replace('(Polska)', '').replace('()', '')
            text = re.sub(r'^[\W_]+|[\W_]+$', '', text).strip()
            if ' - ' in text:
                parts = text.split(' - ')
                if len(parts) == 2 and parts[0].strip() == parts[1].strip():
                    return parts[0].strip()
            return text if text else None

        try:
            map_header = soup.find('p', string=re.compile('Znajdź na mapie'))
            location_tag = None
            if map_header:
                parent_div = map_header.find_parent('div')
                if parent_div:
                    link_tag = parent_div.find('a') or parent_div.find('p')
                    location_tag = link_tag

            if location_tag:
                full_text = location_tag.get_text(strip=True).replace('(Polska)', '').strip()
                zip_match = re.search(r'(\d{2}[-\s]\d{3})\s+([^,]+)', full_text)
                parts = [p.strip() for p in full_text.split(',') if p.strip()]
                
                if zip_match:
                    clean_city = clean_name(zip_match.group(2).strip())
                    loc_data['location_city'] = clean_city
                    loc_data['location_district'] = clean_city 
                    if len(parts) >= 1:
                        raw_voivodeship = clean_name(parts[-1])
                        if raw_voivodeship and clean_city and raw_voivodeship.lower() != clean_city.lower():
                             loc_data['location_voivodeship'] = raw_voivodeship
                else:
                    if len(parts) >= 1: loc_data['location_voivodeship'] = clean_name(parts[-1])
                    if len(parts) >= 3:
                        loc_data['location_city'] = clean_name(parts[0])
                        loc_data['location_district'] = clean_name(parts[1])
                    elif len(parts) <= 2 and len(parts) > 0:
                        loc_data['location_city'] = clean_name(parts[0])

            if loc_data['location_city']:
                city_lower = loc_data['location_city'].lower()
                if city_lower in MAJOR_CITIES_MAP:
                    loc_data['location_voivodeship'] = MAJOR_CITIES_MAP[city_lower]

        except Exception as e:
            logging.warning(f"Location extraction error: {e}")
        return loc_data

    def _extract_image_urls(self, soup: BeautifulSoup) -> str:
        image_urls = []
        try:
            images = soup.find_all('img', attrs={"data-testid": re.compile(r'gallery-image-\d+')})
            for img in images:
                src = img.get('src')
                if src and "http" in src:
                    image_urls.append(src)
            image_urls = list(dict.fromkeys(image_urls))
        except Exception:
            pass
        return ";".join(image_urls)

    def _extract_tech_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
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
                paragraphs = div.find_all('p')
                if len(paragraphs) >= 2: data[my_key] = paragraphs[1].get_text(strip=True)
                elif len(paragraphs) == 1: data[my_key] = paragraphs[0].get_text(strip=True)
                else: data[my_key] = div.get_text(strip=True)
        return data

    def parse_offer(self, url: str) -> Optional[Dict[str, Any]]:
        logging.info(f"Processing offer: {url}")
        response = self.client.get(url)
        if not response: return None

        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')
        
        desc_div = soup.find('div', {'data-testid': 'textWrapper'})
        description = desc_div.get_text(separator='\n', strip=True) if desc_div else ""
        
        title_tag = soup.find('h1', class_='offer-title') or soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else "Unknown"

        price_info = self._extract_price_html(soup)
        loc_info = self._extract_location_html(soup)
        tech_data = self._extract_tech_data(soup)
        images_str = self._extract_image_urls(soup)

        offer_data = {
            "link": url,
            "title": title,
            "description": description,
            "image_urls": images_str,
            **price_info,
            **loc_info,
        }

        for key, value in tech_data.items():
            if key in ["year", "mileage_km", "engine_capacity_cm3", "power_hp", "doors", "seats"]:
                offer_data[key] = self._clean_numeric(value)
            elif key in ["accident_free", "damaged", "first_owner", "registered_pl", "has_registration"]:
                offer_data[key] = self._parse_bool(value)
            else:
                offer_data[key] = value

        return offer_data