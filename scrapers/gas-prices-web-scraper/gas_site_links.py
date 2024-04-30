from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import pickle

class GasSiteLinks:
    def __init__(self, us_site='https://www.fueleconomy.gov/feg/gasprices/states/index.shtml'):
        self.us_site = us_site
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        self.us_links = None
        self.cad_links = None

    def scrape_us_state_links(self):
        print('Fetching US State Links')
        response = requests.get(self.us_site, headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        self.us_links = []
        for area in soup.find_all('area'):
            href = area['href']
            alt = area['alt']
            link = f'https://www.fueleconomy.gov/feg/gasprices/states/{href}'
            state_code = href.split('.')[0]
            self.us_links.append({'link': link, 'name': alt, 'state_code': state_code, 'area_links': []})

    def scrape_us_area_links(self, us_state_dict):
        response = requests.get(us_state_dict['link'], headers=self.headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        city_prices_div = soup.find('div', class_='row city-prices')
        area_links = [link['href'] for link in city_prices_div.find_all('a')] if city_prices_div else []
        # Extract domain
        area_links = [urlparse(link).netloc for link in area_links]
        # Make unique
        area_links = list(set(area_links))
        return area_links
    
    def get_us_links(self):
        if self.us_links is None:
            self.scrape_us_state_links()
        for state in self.us_links:
            print(f"Getting {state['name']} area links")
            state['area_links'] = self.scrape_us_area_links(state)
        return self.us_links

    def save_us_links(self, file_path):
        with open(file_path, 'wb') as f:
            pickle.dump(self.us_links, f)

    def get_cad_links(self):
        self.cad_links = [
            {'link': '', 'city_links': ['http://www.bcgasprices.com/'], 'name': 'British Columbia', 'state_code': 'BC'},
            {'link': '', 'city_links': ['http://www.ontariogasprices.com/'], 'name': 'Ontario', 'state_code': 'ON'},
            {'link': '', 'city_links': ['https://www.nwtgasprices.com/'], 'name': 'North West Territories', 'state_code': 'NT'},
            {'link': '', 'city_links': ['http://www.albertagasprices.com/'], 'name': 'Alberta', 'state_code': 'AB'},
            {'link': '', 'city_links': ['http://www.saskgasprices.com/'], 'name': 'Saskatchewan', 'state_code': 'SK'},
            {'link': '', 'city_links': ['http://www.manitobagasprices.com/'], 'name': 'Manitoba', 'state_code': 'MB'},
            {'link': '', 'city_links': ['http://www.quebecgasprices.com/'], 'name': 'Quebec', 'state_code': 'QC'},
            {'link': '', 'city_links': ['http://www.peigasprices.com/'], 'name': 'Prince Edward Island', 'state_code': 'PE'},
            {'link': '', 'city_links': ['http://www.newbrunswickgasprices.com/'], 'name': 'New Brunswick', 'state_code': 'NB'},
            {'link': '', 'city_links': ['http://www.newfoundlandgasprices.com/'], 'name': 'Newfoundland', 'state_code': 'NF'},
            {'link': '', 'city_links': ['http://www.novascotiagasprices.com/'], 'name': 'Nova Scotia', 'state_code': 'NS'}
        ]
        return self.cad_links
    
    def get_links(self):
        cad_links = self.get_cad_links()
        us_links = self.get_us_links()
        return cad_links + us_links
    
"""if __name__ == "__main__":
    gas_sites = GasSiteLinks('https://www.fueleconomy.gov/feg/gasprices/states/')
    us_sites = gas_sites.get_us_dict()
    print(us_sites)
    gas_sites.save_us_links('./us_sites.pkl')"""

    
"""
[{'city_links': ['www.Birminghamgasprices.com',
                 'www.Mobilegasprices.com',
                 'www.Huntsvillegasprices.com',
                 'www.Montgomerygasprices.com',
                 'www.mapquest.com'],
  'link': 'https://www.fueleconomy.gov/feg/gasprices/states/AL.shtml',
  'state': 'Alabama'},
 {'city_links': ['www.phoenixgasprices.com', 'www.tucsongasprices.com'],
  'link': 'https://www.fueleconomy.gov/feg/gasprices/states/AZ.shtml',
  'state': 'Arizona'},
 {'city_links': ['www.LittleRockgasprices.com'],
  'link': 'https://www.fueleconomy.gov/feg/gasprices/states/AR.shtml',
  'state': 'Arkansas'}]
"""