import logging
from src.wikipedia_scraper import WikipediaScraper
import time
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Wikipedia Scraper Output Format")
    parser.add_argument('-t', '--type', choices=['json', 'csv'], required=True, help="Output file type: 'json' for JSON, 'csv' for CSV")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    start = time.time()

    with WikipediaScraper() as scraper:
        countries = scraper.get_countries()
        for country in countries:
            scraper.get_leaders(country)
        
        scraper.add_first_wiki_par()
        if args.type == 'json':
            scraper.to_json_file()
        else:
            scraper.to_csv_file()
    end = time.time()
    print(f"Total scraping time: {end - start:.2f} seconds")
