import requests
from bs4 import BeautifulSoup
import sqlite3
from pymongo import MongoClient
from datetime import datetime
from pprint import pprint
from dotenv import load_dotenv
import os
load_dotenv()

def get_quotes():
    """
    Retrieves forex quotes from centralcharts.com and returns a list of dictionaries containing 
    the base currency, quote currency, price, and scrape time.

    Returns:
    list: A list of dictionaries representing the forex quotes.
    """
    url = "https://www.centralcharts.com/en/price-list-ranking/ALL/asc/ts_507-usd-currency-pairs--qc_1-alphabetical-order"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    print('Getting Quotes')
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', class_='tabMini tabQuotes')
    tbody = table.find('tbody')
    trs = tbody.find_all('tr')

    quotes = []
    for tr in trs:
        tds = tr.find_all('td')
        symbol = tds[0].text.strip()
        price = tds[1].text.strip()
        base, quote = symbol[-7:].split('/')
        price = float(price.replace(',', ''))

        if base != 'USD':
            base, quote = quote, base
            price = 1 / price

        scrape_time = datetime.now()
        quote_info = {
            'base': base,
            'quote': quote,
            'price': price,
            'scrape_time': scrape_time
        }

        quotes.append(quote_info)
    print(f'Got {len(quotes)} forex quotes')
    return quotes

def insert_raw_forex_mongodb(quotes):
    """
    Inserts raw forex quotes into the 'forex-raw' collection

    Parameters:
    quotes (list): A list of dictionaries representing the forex quotes to be inserted.

    Returns:
    None
    """
    print('Inserting raw forex quotes')
    mongo_uri = os.getenv('MONGODB_URI')
    client = MongoClient(mongo_uri)
    db = client['gasplit']
    collection = db['forex-raw']
    collection.insert_many(quotes)
    client.close()
    print('Insert Complete')

def generate_quote_pairs(quotes):
    symbols = [quote['base'] for quote in quotes] + [quote['quote'] for quote in quotes]
    symbols = list(set(symbols))
    pairs = []
    for base in symbols:
        for quote in symbols:
            if base != quote:
                pairs.append({'base': base, 'quote': quote})
    print(f'Created {len(pairs)} forex pairs')
    return pairs

def get_pair_price(quotes, base, quote):
    """
    Returns the price of a currency pair using the USD as an intermediary.

    Parameters:
    quotes (list): A list of dictionaries representing the forex quotes.
    base (str): The base currency.
    quote (str): The quote currency.

    Returns:
    float: The price of the currency pair.
    """
    # All quotes are calculated with USD as an intermediary
    # Quotes which already use USD (is USD/EUR) need a USD to USD 
    # Quote in the quotes array to compare through.
    quotes.append({'base': 'USD', 'quote': 'USD', 'price': 1})
    usd_to_base = usd_to_quote = None
    for quote_info in quotes:
        if quote_info['base'] == 'USD' and quote_info['quote'] == base:
            usd_to_base = quote_info['price']
        elif quote_info['base'] == 'USD' and quote_info['quote'] == quote:
            usd_to_quote = quote_info['price']

    if usd_to_base is None or usd_to_quote is None:
        print(f"No quote found for base currency: {base} to {quote}")
        return 0

    return usd_to_quote / usd_to_base

def insert_forex_quotes_mongodb(quotes):
    """
    Inserts forex quotes into the 'forex-quotes' collection

    Parameters:
    quotes (list): A list of dictionaries representing the forex quotes to be inserted.
    """
    print('Inserting forex quotes')
    mongo_uri = os.getenv('MONGODB_URI')
    client = MongoClient(mongo_uri)
    db = client['gasplit']
    collection = db['forex-quotes']
    collection.insert_many(quotes)
    client.close()

def main():
    quotes = get_quotes()
    insert_raw_forex_mongodb(quotes)
    pairs = generate_quote_pairs(quotes)
    print('Calculating pair prices')
    quotes_array = []
    for currency in pairs:
        base = currency['base']
        quote = currency['quote']
        price = get_pair_price(quotes, base, quote)
        if price == 0:
            continue
        quote_time = datetime.now()
        quotes_array.append({ 
            'base': base, 
            'quote': quote, 
            'price': price, 
            'quote_time': quote_time })
    print(f'Calculated prices for {len(quotes_array)}/{len(pairs)} pairs')
    insert_forex_quotes_mongodb(quotes_array)
    print('Forex Scrape Complete!')

if __name__ == "__main__":
    main()