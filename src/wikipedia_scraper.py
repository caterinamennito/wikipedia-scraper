from requests import Session
import re
from bs4 import BeautifulSoup
import concurrent.futures
import json
import functools


def authenticated(function):
    @functools.wraps(function)
    def decorated(*args, **kwargs):
        if not args[0].session:
            raise ValueError("Session is not initialized. Please use the context manager.")
        return function(*args, **kwargs)
    return decorated

class WikipediaScraper:

    def __init__(self):
        self.base_url = "https://country-leaders.onrender.com"
        self.leaders_endpoint = "/leaders"
        self.countries_endpoint = "/countries"
        self.cookies_endpoint = "/cookie"
        self.leaders_data = {}
        self.session = None

    def __enter__(self):
        self.session = Session()
        self.__set_cookies()
        print('session created')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"Exception: {exc_type}, {exc_val}, {exc_tb}")
        if self.session:
            self.session.close()
    
    def __call__(self, *args):
        pass
    


    @authenticated
    def __set_cookies(self):
        self.session.get(f"{self.base_url}{self.cookies_endpoint}") # type: ignore


    @authenticated
    def get_countries(self):
        countries_req = self.session.get(f"{self.base_url}{self.countries_endpoint}") # type: ignore
        print("session", self.session, countries_req)
        return countries_req.json()

    @authenticated
    def get_leaders(self, country: str):
        params = {"country": country}
        req = self.session.get(f"{self.base_url}{self.leaders_endpoint}", params=params) # type: ignore
        self.leaders_data[country] = req.json()
    
    def __p_followed_by_b(self, tag):
        if tag.name == "p" and tag.next_element and tag.next_element.name == "b":
            return True
        else:
            return False
    
    @authenticated
    def get_first_paragraph(self, wikipedia_url: str):
        """returns the first paragraph (defined by the HTML tag <p>) with details about the leader"""
        wiki_html = self.session.get(wikipedia_url).text # type: ignore
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
            # Checking if the cleaned text is empty
            if not cleaned.strip():
                return "No information available.", wikipedia_url
            return cleaned.strip()
    
    def add_first_wiki_par(self):
        for leaders in self.leaders_data.values():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                leaders_wiki_urls = [leader["wikipedia_url"] for leader in leaders]
                paragraphs = list(executor.map(self.get_first_paragraph, leaders_wiki_urls))
                for leader, par in zip(leaders, paragraphs):
                    leader["first_wiki_par"] = par

    
    def to_json_file(self, filepath: str = "./leaders.json"):
        with open(filepath, "w", encoding="utf8") as leaders_file:
            leaders_file.write(json.dumps(self.leaders_data, ensure_ascii=False))
