from gas_site_links import GasSiteLinks
from gas_site import GasSite
import sqlite3
from datetime import datetime

def check_tables_exist():
    conn = sqlite3.connect('../gas.sqlite')
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gas_prices'")
    if cursor.fetchone() is None:
        cursor.execute('''
            CREATE TABLE gas_prices (
                id TEXT PRIMARY KEY,
                price REAL,
                dt TEXT,
                city_id INTEGER
            )
        ''')
        conn.commit()


    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='states'")
    if cursor.fetchone() is None:
        cursor.execute('''
            CREATE TABLE states (
                id INTEGER PRIMARY KEY,
                country TEXT,
                name TEXT UNIQUE,
                code TEXT
            )
        ''')
        conn.commit()



    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cities'")
    if cursor.fetchone() is None:
        cursor.execute('''
            CREATE TABLE cities (
                id INTEGER PRIMARY KEY,
                name TEXT,
                identifier TEXT,
                url TEXT,
                state_id INTEGER
            )
        ''')
        conn.commit()

    conn.close()

def main():
    gas_site_links = GasSiteLinks()
    na_array = gas_site_links.get_links()
    check_tables_exist()

    conn = sqlite3.connect('../gas.sqlite')
    cursor = conn.cursor()

    for state in na_array[:4]:
        # Get the current state's state id
        cursor.execute("SELECT id FROM states WHERE name=?", (state['name'],))
        state_id = cursor.fetchone()
        if state_id:
            state_id = state_id[0]
        else:
            cursor.execute("INSERT INTO states VALUES (NULL, 'USA', ?, ?)", (state['name'], state['state_code']))
            conn.commit()
            state_id = cursor.lastrowid
        
        print(f"State: {state['name']}, {state_id}")
        # Loop the areas in the state
        for area_link in state['area_links']:
            gas_site = GasSite(area_link)
            gas_site.fetch_soup()
            if not gas_site.is_gasbuddy:
                print('Not a Gasbuddy site')
                continue
            # Get the cities in that area's site and loop them
            city_list = gas_site.get_city_list()
            for city in city_list:
                if city['name'] == 'All Areas':
                    continue
                # Get the city's id
                cursor.execute("SELECT id FROM cities WHERE identifier=?", (city['identifier'],))
                city_id = cursor.fetchone()
                if city_id:
                    city_id = city_id[0]
                else:
                    cursor.execute("INSERT INTO cities (name, identifier, url, state_id) VALUES (?, ?, ?, ?)", 
                                (city['name'], city['identifier'], city['url'], state_id))
                    conn.commit()
                    city_id = cursor.lastrowid
                # Parse the city's gas page as its own site, and get its gas prices
                city_gas_page = GasSite(city['url'])
                city_gas_page.fetch_soup()
                gas_prices = city_gas_page.parse_gas_prices()
                print(f"City Name: {city['name']}, {city_id}, has {len(gas_prices)} prices")
                price_list = [(price['ref_id'], price['price'], datetime.strftime(price['dt'], '%Y-%m-%d %H:%M:%S'), city_id) for price in gas_prices]
                cursor.executemany('INSERT OR IGNORE INTO gas_prices VALUES (?, ?, ?, ?)', price_list)
        conn.commit()

    conn.close()

if __name__ == "__main__":
    main()