import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from pymongo import MongoClient

from PIL import Image
import base64
from io import BytesIO
from dotenv import load_dotenv
import os
load_dotenv()
from pprint import pprint

def get_base_64_img(url):
    image_base64 = None
    try:
        response = requests.get(url)
        image_file = BytesIO(response.content)
        image_file.seek(0)
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print('Error getting B64 Image')
        print(e)
    return image_base64

def get_years():
    """
    Fetches a list of available years from the fueleconomy.gov API.

    Returns:
        list: A list of integers representing the available years.
    """
    url = "https://www.fueleconomy.gov/ws/rest/vehicle/menu/year"
    response = requests.get(url)
    # Check if the request was successful
    if response.status_code != 200:
        return ValueError('Failed to fetch years')
    root = ET.fromstring(response.content)
    return [int(menuItem.find('value').text) for menuItem in root.findall('.//menuItem')]

def get_makes(year_min, year_max):
    """
    Fetches a list of available makes for a given range of years from the fueleconomy.gov API.

    Args:
        year_min (int): The minimum year.
        year_max (int): The maximum year.

    Returns:
        list: A list of strings representing the available makes.
    """
    url = f'https://www.fueleconomy.gov/feg/Find.do?action=getMenuMakeRng&year1={year_min}&year2={year_max}'
    response = requests.get(url)
    data = response.json()
    makes = [item['value'] for item in data['options']]
    return makes

def get_models(year1, year2, make):
    """
    Fetches a list of available models for a given range of years and make from the fueleconomy.gov API.

    Args:
        year1 (int): The minimum year.
        year2 (int): The maximum year.
        make (str): The make of the vehicle.

    Returns:
        list: A list of strings representing the available models.
    """
    url = f'https://www.fueleconomy.gov/feg/Find.do?action=getMenuBaseModelRng&year1={year1}&year2={year2}&make={make}'
    response = requests.get(url)
    data = response.json()
    models = [item['value'] for item in data['options']]
    return models

def get_car_data(make, model, year):
    """
    Fetches car data for a given make, model, and year from the fueleconomy.gov API.

    Args:
        make (str): The make of the vehicle.
        model (str): The model of the vehicle.
        year (int): The year of the vehicle.

    Returns:
        list: A list of dictionaries containing the car data, including the year, make, model, name, trim, fuel, units, MPG, city MPG, and highway MPG.
    """
    try:
        url = f'https://www.fueleconomy.gov/feg/PowerSearch.do?action=noform&path=1&year={year}&make={make}&baseModel={model}&srchtyp=ymm&pageno=1&rowLimit=200&sortBy=Comb&tabView=0'
        response = requests.get(url)
        # If only a single car is returned from the URL, fec retuns a different page
        # Looks like this: https://www.fueleconomy.gov/feg/Find.do?action=sbs&id=47477
        soup = BeautifulSoup(response.content, 'html.parser')
        single_car = 'Compare Side-by-Side' in str(soup)

        car_mpg_list = []

        if (single_car):
            name_elm = soup.find('th', class_='sbsCellHeader')
            name_elm = name_elm.contents[2] if name_elm else None
            name = ' '.join(name_elm.text.strip().split())
            trim = soup.find('tr', class_='specs').text.strip()
            fuel = soup.find('td', class_='fuel nobottomborder padding').text.strip()
            units = soup.find('td', class_='unitsLabel').text.strip()
            mpg_elm = soup.find('td', class_='combinedMPG')
            mpg_elm = mpg_elm.contents[1] if mpg_elm else None
            mpg = int(mpg_elm.text) if mpg_elm else ''
            city_elm, hwy_elm = soup.find_all('td', class_='ctyhwy')[0:2]
            city_elm = city_elm.contents[1] if city_elm else None
            hwy_elm = hwy_elm.contents[1] if hwy_elm else None
            city = int(city_elm.text) if city_elm else ''
            hwy = int(hwy_elm.text) if hwy_elm else ''
            range_elm = soup.find('div', class_='totalRange')
            total_range = range_elm.contents[0].text.strip() if range_elm else None
            
            img_elm = soup.find('img', src=lambda s: s and s.startswith('/feg/photos'))
            base_64_image = None
            if (img_elm):
                img_url = f'https://www.fueleconomy.gov{img_elm["src"]}'
                base_64_image = get_base_64_img(img_url)
                
            car_mpg_list.append({
                "year": year,
                "make": make,
                "model": model,
                "name": name,
                "trim": trim,
                "fuel": fuel,
                "units": units,
                "total_range": total_range,
                "fuel_economy": {
                    "combined": mpg,
                    "city": city,
                    "hwy": hwy,
                },
                "img": base_64_image
            })
        else:
            table = soup.find('table', class_='cars display responsive stickyHeader')
            tbody = table.find('tbody')
            trs = tbody.find_all('tr')
            for i in range(0, len(trs)):
                try:
                    tr_class = trs[i].get('class')
                    if tr_class and tr_class[0] == 'ymm-row':
                        # Name of car
                        name = trs[i].find('a').get_text()
                        name = name.strip().replace('\n', '')
                        trim, fuel  = [x.strip() for x in trs[i].find('span').get_text().rsplit(',', 1)]
                        # MPG and Units Elements
                        mpg_elm = trs[i+1].find('td', class_='mpg-comb')
                        units_elm = trs[i+1].find('td', class_='unitsLabel')
                        city_elm, hwy_elm = trs[i+1].find_all('td', class_='ctyhwy')[0:2]
                        # MPG and Units Text
                        mpg = int(mpg_elm.get_text()) if mpg_elm else ''
                        units = units_elm.get_text() if units_elm else ''
                        units = units.strip().replace('\r', '').replace('\t', '').replace('\n', '')
                        city = int(city_elm.get_text()) if city_elm else ''
                        hwy = int(hwy_elm.get_text()) if hwy_elm else ''
                        range_elm = trs[i+5].find('div', class_='totalRange')
                        total_range = range_elm.contents[0].text.strip() if range_elm else None

                        img_elm = trs[i+1].find('img', src=lambda s: s and s.startswith('/feg/photos'))

                        base_64_image = None
                        if (img_elm):
                            img_url = f'https://www.fueleconomy.gov{img_elm["src"]}'
                            base_64_image = get_base_64_img(img_url)
                        
                        car_mpg_list.append({
                            "year": year,
                            "make": make,
                            "model": model,
                            "name": name,
                            "trim": trim,
                            "fuel": fuel,
                            "units": units,
                            "total_range": total_range,
                            "fuel_economy": {
                                "combined": mpg,
                                "city": city,
                                "hwy": hwy,
                            },
                            "img": base_64_image
                        })
                except Exception as e:
                    print(f'Could not parse {make} {model}, {year}')
                    print(e)
        return car_mpg_list
    except Exception as e:
        print(e)
        print(f'Error with {make} {model}, {year}')
        return []


def get_image(year, make, model):
    """
    Fetches an image for a given year, make, and model from the Google API, resizes it to a uniform size, and saves it to a file.

    Args:
        year (int): The year of the vehicle.
        make (str): The make of the vehicle.
        model (str): The model of the vehicle.

    Returns:
        str: A base64-encoded string representing the image.
    """
    # Get a list of images from the Google API
    api_key = os.getenv('GOOGLE_API_KEY')
    searchString = f'{year} {make} {model}'
    url = 'https://www.googleapis.com/customsearch/v1'
    params = {
        'q': searchString,
        'key': api_key,
        'cx': '258f21f411880431c',
        'searchType': 'image',
        'imgSize': 'XLARGE',
        'imgType': 'stock',
        'imgColorType': 'trans'
    }
    
    response = requests.get(url, params=params)
    if (response.status_code != 200):
        return ValueError('Could not connnect to Google Images')
    results = response.json()
    # Find the largest image
    links = [item['link'] for item in results['items']]
    links = [link for link in links if '.svg' not in link.lower()]
    largest_url = None
    largest_size = 0
    for url in links:
        try:
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
        except Exception as e:
            print(f'Error with {url}')
            print(e)
            continue
        # size = img.width * img.height  # product of width and height
        # if size <= largest_size:
        #     continue
        #largest_size = size
        largest_url = url
        break
    # Resize the image to be uniform
    print(largest_url)
    response = requests.get(largest_url)
    img = Image.open(BytesIO(response.content))
    goal_width = 600
    goal_height = 400
    # Check the images orientation relative to our goal aspect ratio
    is_landscape = img.width/img.height > goal_width/goal_height
    # Scale the image so it covers our goal dimensions
    scaled_width = (goal_height/img.height) * img.width if is_landscape else goal_width
    scaled_height = goal_height if is_landscape else (goal_width/img.width) * img.height
    
    img = img.resize((int(scaled_width), int(scaled_height)), Image.ANTIALIAS)
    # Crop the scaled image to our goal dimension
    # Calculate the starting points for the crop
    start_x = (img.width - goal_width) / 2
    start_y = (img.height - goal_height) / 2
    # Calculate the ending points for the crop
    end_x = start_x + goal_width
    end_y = start_y + goal_height
    # Crop the image
    img = img.crop((start_x, start_y, end_x, end_y))
    # Save the image
    
    img.convert('RGBA').save(f'./cars/{year}_{make}_{model}.png')

    with open(f'./cars/{year}_{make}_{model}.png', 'rb') as file:
        img_read = file.read()

    # Convert the image to a base64 string
    return base64.b64encode(img_read)

def insert_new_car_data(year, cars):
    mongo_uri = os.getenv('MONGODB_URI')
    client = MongoClient(mongo_uri)
    db = client['gasplit']
    collection = db['car_mpg']

    # Create a list of existing cars for the given year
    existing_cars = collection.find({'year': year}, {'year': 1, 'make': 1, 'model': 1, 'trim': 1})

    # Create a set of existing cars for fast lookup
    existing_car_set = set((car['year'], car['make'], car['model'], car['trim']) for car in existing_cars)

    # Create a list of new cars to insert
    new_cars = [car for car in cars if (car['year'], car['make'], car['model'], car['trim']) not in existing_car_set]

    # Insert new cars in bulk
    print("\033[91m" + f'{year} - {len(new_cars)} new cars' + "\033[0m")
    if new_cars:
        collection.insert_many(new_cars)

    client.close()
    print('Insert Complete')

def get_all_makes_models_years():
    print('Starting Search')
    years = get_years()
    years = years[:1]
    for year in years:
        cars_in_year = []
        makes = get_makes(year, year)
        for make in makes[:1]:
            models = get_models(year, year, make)
            for model in models:
                car_data = get_car_data(make, model, year)
                cars_in_year += car_data
                print(f'{year} {make} {model} - {len(car_data)} trims')
        print()
        print("\033[91m" + f'{year} - {len(cars_in_year)} total cars' + "\033[0m")
        insert_new_car_data(year, cars_in_year)
        print()
