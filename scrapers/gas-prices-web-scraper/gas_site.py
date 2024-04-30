import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote

class GasSite:
    def __init__(self, url):
        prefix = 'https://' if 'http' not in url else ''
        self.url = prefix + url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        self.soup = None
        self.is_gasbuddy = True
        self.prices = []

    def fetch_soup(self):
        if not self.soup:
            response = requests.get(self.url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            gasbuddy_image = 'https://images.gasbuddy.com/images/websites/gasbuddy/apps/download_gasbuddy_sm.png'
            self.is_gasbuddy = soup.find('img', src=gasbuddy_image) is not None
            self.soup = soup

    def parse_date(self, date_ref):
        # Example of date ref: Mon 12:30 PM
        today = datetime.today()
        today = today.replace(microsecond=0, second=0, minute=0, hour=0)
        day_of_week, time, am_pm = date_ref.split()
        days_of_the_week = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

        # Calculate the pas weekday index starting at Sun = 0
        current_weekday_index = (datetime.today().weekday() - 1) % 7
        ref_weekday_index = days_of_the_week.index(day_of_week)
        day_of_week_diff = current_weekday_index - ref_weekday_index + 2
        day_of_week = today - timedelta(days=day_of_week_diff)
        
        # Calculate the time of that day
        time = datetime.strptime(time, '%I:%M')
        if am_pm.lower() == 'pm':
            time += timedelta(hours=12) if time.hour < 12 else timedelta(hours=0)
        elif am_pm.lower() == 'am':
            time -= timedelta(hours=12) if time.hour == 12 else timedelta(hours=0)
        date = day_of_week.replace(hour=time.hour, minute=time.minute)
        return date

    def get_city_list(self):
        select_element = self.soup.find('select', {'id': 'ctl00_Content_P_PSC1_lstAreas'})
        options = select_element.find_all('option')
        city_list = [{
            'identifier': option['value'], 
            'name': option.text,
            'url': urljoin(self.url, 'GasPriceSearch.aspx?typ=adv&tme_limit=24&area=' + quote(option['value']))
            } for option in options]
        return city_list
    
    def parse_gas_prices(self):
        table = self.soup.find('table', {'class': 'p_v2'})
        rows = table.find_all('tr')
        self.prices = []
        for row in rows:
            ph_value = row.get('ph')
            if not ph_value:
                continue
            price_elem = row.find('div', class_='price_num')
            gas_price = price_elem.text if price_elem else None
            time_elem = row.find('div', class_='tm')
            date_time = time_elem['title'] if time_elem and 'title' in time_elem.attrs else None
            date_time = self.parse_date(date_time) if date_time else None
            ref_id = ph_value + '_' + str(int(date_time.timestamp()))
            data_dict = {'ref_id': ref_id, 'price': gas_price, 'dt': date_time}
            self.prices.append(data_dict)
        return self.prices
    
if __name__ == "__main__":
    gas_site = GasSite("http://www.ontariogasprices.com/GasPriceSearch.aspx?typ=adv&tme_limit=24&area=White%20River")
    gas_site.fetch_soup()
    if not gas_site.is_gasbuddy:
        print('Site is not GasBuddy')
        exit()
    # cities = gas_site.get_city_list()
    # print(cities)

    prices = gas_site.parse_gas_prices()
    print(prices)