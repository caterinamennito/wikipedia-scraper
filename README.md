# Wikipedia Scraper

A Python project for querying an API to obtain a list of countries and their past political leaders, extract and sanitize their short bio from Wikipedia and save the data as JSON or CSV file.

## Features

- Fetches a list of countries and their leaders from an [API](https://country-leaders.onrender.com/docs#/)
- Scrapes the first paragraph of the leaders' bio from Wikipedia pages.
- Parses and processes the scraped data.
- Outputs results in JSON or CSV format.


## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/caterinamennito/wikipedia-scraper.git
    cd wikipedia-scraper
    ```

2. (Recommended) Create and activate a virtual environment:
    ```sh
    python3 -m venv clean_venv
    source clean_venv/bin/activate
    ```

3. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

To run the scraper from the command line:
```sh
python main.py -t json
```
To run the scraper and save the output in CSV format:
```sh
python main.py -t csv
```
