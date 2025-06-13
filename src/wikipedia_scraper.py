from requests import Session, RequestException, adapters
import re
from bs4 import BeautifulSoup, element as bs4_element
import concurrent.futures
import json
import functools
import logging
from typing import Any, Dict, List, Optional

def authenticated(function):
    @functools.wraps(function)
    def decorated(*args, **kwargs):
        if not args[0].session:
            raise ValueError("Session is not initialized. Please use the context manager.")
        return function(*args, **kwargs)
    return decorated

class WikipediaScraper:
    """
    Scrapes the first Wikipedia paragraphs of some country leaders.
    """

    def __init__(self):
        self.base_url: str = "https://country-leaders.onrender.com"
        self.leaders_endpoint: str = "/leaders"
        self.countries_endpoint: str = "/countries"
        self.cookies_endpoint: str = "/cookie"
        self.leaders_data: Dict[str, List[Dict[str, Any]]] = {}
        self.session: Optional[Session] = None

    def __enter__(self) -> "WikipediaScraper":
        self.session = Session()
        # Increase the connection pool size 
        adapter = adapters.HTTPAdapter(pool_connections=10, pool_maxsize=50)
        self.session.mount('https://', adapter)
        self.__set_cookies()
        logging.info('Session created')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logging.error(f"Exception: {exc_type}, {exc_val}, {exc_tb}")
        if self.session:
            self.session.close()
            logging.info('Session closed')

    @authenticated
    def __set_cookies(self) -> None:
        try:
            self.session.get(f"{self.base_url}{self.cookies_endpoint}") # type: ignore
        except RequestException as e:
            logging.error(f"Failed to set cookies: {e}")
            raise

    @authenticated
    def get_countries(self) -> List[str]:
        """
        Fetches the list of countries.
        """
        try:
            countries_req = self.session.get(f"{self.base_url}{self.countries_endpoint}") # type: ignore
            countries_req.raise_for_status()
            logging.info("Fetched countries successfully.")
            return countries_req.json()
        except RequestException as e:
            logging.error(f"Failed to fetch countries: {e}")
            return []

    @authenticated
    def get_leaders(self, country: str) -> None:
        """
        Fetches leaders for a given country and stores them in leaders_data.
        """
        params = {"country": country}
        try:
            req = self.session.get(f"{self.base_url}{self.leaders_endpoint}", params=params) # type: ignore
            req.raise_for_status()
            self.leaders_data[country] = req.json()
            logging.info(f"Fetched leaders for {country}.")
        except RequestException as e:
            logging.error(f"Failed to fetch leaders for {country}: {e}")
            self.leaders_data[country] = []

    @authenticated
    def __get_first_paragraph(self, wikipedia_url: str) -> str:
        """
        Returns the first paragraph with details about the leader.
        """
        try:
            wiki_html = self.session.get(wikipedia_url, timeout=10).text # type: ignore
            soup = BeautifulSoup(wiki_html, "html.parser")
            
            # Extract the language from the URL
            lang = wikipedia_url.split("/")[2].split(".")[0]

            # Find first <div> tag with attribute lang=<lang>
            first_div = soup.find("div", {'lang': lang})

            # Find all <p> tags within that <div> before another <div> tag
            if first_div and isinstance(first_div, bs4_element.Tag):
                first_paragraph = ''
                for tag in first_div.find_all("p", recursive=False):
                    first_paragraph += tag.get_text() + " "
                    next_tag = tag.find_next_sibling()
                    # Stop if the next sibling is a <div>
                    if next_tag and getattr(next_tag, "name", None) == "div":
                        break

                # Remove \n
                first_paragraph = first_paragraph.replace("\n", " ")
                # Remove [ ... ]
                first_paragraph = re.sub(r"\[.*?\]", "", first_paragraph)
                # Remove / ... / and optional ;
                first_paragraph = re.sub(r"/.*?/;?", "", first_paragraph)
                # Remove (word ⓘ) or word ⓘ, including the first ( before ⓘ if followed by )
                first_paragraph = re.sub(r"\s*\([^\(\)]*?\b\w+\s*ⓘ\)", "", first_paragraph)  # (word ⓘ)
                first_paragraph = re.sub(r"\s*\b\w+\s*ⓘ", "", first_paragraph)  # word ⓘ
                if not first_paragraph.strip():
                    return "No information available."
                return first_paragraph.strip()
            else:
                return "No information available."
        except Exception as e:
            logging.error(f"Error parsing Wikipedia page: {wikipedia_url} - {e}")
            return "No information available."

    def add_first_wiki_par(self) -> None:
        """
        Adds the first Wikipedia paragraph to each leader in leaders_data.
        """
        wiki_urls = []
        leaders_data_values = self.leaders_data.values()
        for leaders in leaders_data_values:
            wiki_urls.extend(leader["wikipedia_url"] for leader in leaders)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            paragraphs = list(executor.map(self.__get_first_paragraph, wiki_urls))

        # Flatten the list of leaders
        all_leaders = sum(leaders_data_values, [])
        for leader, par in zip(all_leaders, paragraphs):
            leader["first_wiki_par"] = par

    def to_json_file(self, filepath: str = "./leaders.json") -> None:
        """
        Writes leaders_data to a JSON file.
        """
        try:
            with open(filepath, "w", encoding="utf8") as leaders_file:
                json.dump(self.leaders_data, leaders_file, ensure_ascii=False)
            logging.info(f"Leaders data written to {filepath}")
        except Exception as e:
            logging.error(f"Failed to write JSON file: {e}")

    def to_csv_file(self, filepath: str = "./leaders.csv") -> None:
        """
        Writes leaders_data to a CSV file using pandas.
        """
        try:
            import pandas as pd
            # Flatten leaders_data into a list of dicts, adding country info
            flat_data = []
            for country, leaders in self.leaders_data.items():
                for leader in leaders:
                    leader_row = leader.copy()
                    leader_row["country"] = country
                    flat_data.append(leader_row)
            df = pd.DataFrame(flat_data)
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            logging.info(f"Leaders data written to {filepath}")
        except ImportError:
            logging.error("pandas is not installed. Cannot write to CSV file.")
        except Exception as e:
            logging.error(f"Failed to write CSV file: {e}")