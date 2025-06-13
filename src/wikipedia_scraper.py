from requests import Session, RequestException
import re
from bs4 import BeautifulSoup
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

    @staticmethod
    def __p_followed_by_b(tag) -> bool:
        return tag.name == "p" and getattr(tag.next_element, "name", None) == "b"

    @authenticated
    def __get_first_paragraph(self, wikipedia_url: str) -> str:
        """
        Returns the first paragraph with details about the leader.
        """
        try:
            wiki_html = self.session.get(wikipedia_url, timeout=10).text # type: ignore
            soup = BeautifulSoup(wiki_html, "html.parser")
            first_paragraph_tag = soup.find(self.__p_followed_by_b)

            if first_paragraph_tag:
                raw_text = first_paragraph_tag.get_text()
                # Remove [ ... ]
                cleaned = re.sub(r"\[.*?\]", "", raw_text)
                # Remove / ... / and optional ;
                cleaned = re.sub(r"/.*?/;?", "", cleaned)
                # Remove (word ⓘ) or word ⓘ, including the first ( before ⓘ if followed by )
                cleaned = re.sub(r"\s*\([^\(\)]*?\b\w+\s*ⓘ\)", "", cleaned)  # (word ⓘ)
                cleaned = re.sub(r"\s*\b\w+\s*ⓘ", "", cleaned)  # word ⓘ
                if not cleaned.strip():
                    return "No information available."
                return cleaned.strip()
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