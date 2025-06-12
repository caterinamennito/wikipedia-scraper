from src.wikipedia_scraper import WikipediaScraper

if __name__ == '__main__':
    with WikipediaScraper() as scraper:
        countries = scraper.get_countries()
        for country in countries:
            scraper.get_leaders(country)
        
        scraper.add_first_wiki_par()
        scraper.to_json_file()
