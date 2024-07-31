# Talkshow Scrapper

## Overview
German political talk shows are my guilty pleasure. Most of the high-profile ones are available as audio files or podcasts.
'Markus Lanz' is not. This Python script is designed to automate the process of downloading and converting episodes from the ZDF Mediathek. It fetches episode details, allows you to select which episodes to download, downloads the episodes in WebM format, converts them to MP3, and adds metadata to the MP3 files.

## Requirements
- Python 3.6 or higher
- `selenium` for web scraping
- `requests` for HTTP requests
- `moviepy` for media conversion
- `mutagen` for adding metadata

You will also need the Chrome WebDriver to run Selenium with Chrome.
