import os
import re
import datetime as dt
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from moviepy.editor import VideoFileClip
from mutagen.easyid3 import EasyID3

URL = "https://www.zdf.de/gesellschaft/markus-lanz"

def broadcast_time_constructor(date_string):
    """Generate possible broadcast times based on the given date string."""
    date_object = dt.datetime.strptime(date_string, "%d.%m.%Y") + dt.timedelta(days=1)
    possible_times = [date_object - i * dt.timedelta(minutes=15) for i in range(16)]
    return possible_times

def popup_acceptor(zdf_webpage_driver_instance):
    """Accept the popup if it appears."""
    popup_button = zdf_webpage_driver_instance.find_element(By.CSS_SELECTOR, "#zdf-cmp-deny-btn")
    popup_button.click()

def get_guest_talking_points(episode_url):
    """Retrieve guest talking points from a specific episode URL."""
    download_chrome_options = Options()
    download_chrome_options.add_argument('--headless')  # Run Chrome in headless mode
    download_chrome_options.add_argument('--no-sandbox')  # Disable sandbox for headless mode
    download_chrome_options.add_argument('--log-level=3')  # Set log level to suppress unnecessary logs
    download_driver = webdriver.Chrome(options=download_chrome_options)
    download_driver.get(url=episode_url)
    popup_acceptor(download_driver)
    guest_talking_points = download_driver.find_element(By.CSS_SELECTOR, ".b-post-content").text
    download_driver.quit()
    return guest_talking_points

def scan_episodes(description_webdriver):
    """Retrieve and parse episode information from the webpage."""
    print("Retrieving episode information...")
    episodes_box = description_webdriver.find_element(By.CSS_SELECTOR, "div.tile-box-wrap.showmore-wrapper")
    episode_boxes = episodes_box.find_elements(By.CSS_SELECTOR, ".b-cluster-teaser.b-vertical-teaser")
    full_info = {}
    for i, episode_box in enumerate(episode_boxes):
        button = episode_box.find_element(By.CSS_SELECTOR, ".teaser-open-btn")
        button.click()
        episode_number = i + 1
        episode_date = episode_box.find_element(By.CSS_SELECTOR, ".teaser-extended-info").text.strip()

        info_text = episode_box.find_element(By.CSS_SELECTOR, ".teaser-extended-text").text.strip()

        url_to_video_page = episode_box.find_element(By.CSS_SELECTOR, ".teaser-play-btn.button").get_attribute('href')
        guest_talking_points = "\n" + get_guest_talking_points(url_to_video_page)

        pattern = r'^\s([^,]+)'
        guest_names = re.findall(pattern, guest_talking_points, re.MULTILINE)

        full_info[episode_date] = {
            "episode_number": episode_number,
            "info_text": info_text,
            "guest_talking_points": guest_talking_points,
            "guest_names": guest_names,
        }
        if i >= 8:
            break

    return full_info

def episode_picker(full_info):
    """Prompt user to select episodes and return the selected episodes."""
    print("These are the most recent episodes:\n")
    for date, details in reversed(full_info.items()):
        print(f'Episode Number: {details.get("episode_number", "Not available.")}')
        print(f'Date: {date}')
        print(f'Content: {details.get("info_text", "Not available.")}\n')
        print(f'Talking Points:{details.get("guest_talking_points", "Not available.")}\n')
        print("\n------------------------------")

    matches = None
    pattern = r'\d'
    while not matches:
        string = input("Which of these episodes do you want to download? For example, type '1, 4, 5'.\nYour answer: ")
        matches = re.findall(pattern, string)
        if not matches:
            print("No matching episode numbers for your input. Try again.\n")
    selected_numbers = [int(num_string) for num_string in matches]


    date_selection = [date for i, date in enumerate(full_info.keys()) if i + 1 in selected_numbers]
    full_info_selection = {date: full_info[date] for date in date_selection}
    return full_info_selection

def add_episode_urls(selected_episode_info):
    """Add download URLs to the selected episodes."""
    for date in selected_episode_info:
        plausible_times = broadcast_time_constructor(date)
        potential_links = []
        for time in plausible_times:
            dt_fragment2 = time.strftime("%y%m%d_%H%M")
            dt_fragment1 = time.strftime("%y/%m")
            link = f"https://nrodlzdf-a.akamaihd.net/none/zdf/{dt_fragment1}/{dt_fragment2}_sendung_mla/1/{dt_fragment2}_sendung_mla_368k_p16v17.webm"

            potential_links.append(link)

        for url in potential_links:
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                selected_episode_info[date]["url"] = url
                return selected_episode_info

def download_episodes(info_dict):
    """Download and convert episodes from the provided information dictionary."""
    for i, (date, info) in enumerate(info_dict.items()):
        url = info["url"]
        episode_total = len(info_dict)
        show_prefix = "_".join(URL.split("/")[-1].split("-")).title()
        webm_file_path = f"./episodes/{show_prefix}_vom_" + date + "f.webm"
        mp3_file_path = f"./episodes/{show_prefix}_vom_" + date + ".mp3"
        print(f"Downloaded mp3 files will be saved under:\n{os.getcwd() + '/episodes/'}")
        if not os.path.exists(mp3_file_path):
            if not os.path.exists(webm_file_path):
                print(f"Requesting episode {i + 1}/{episode_total}...")
                response = requests.get(url, stream=True, timeout=10)
                if response.status_code == 200:
                    print(f"Downloading episode {i + 1}/{episode_total}...")
                    with open(webm_file_path, 'wb') as webm_file:
                        for chunk in response.iter_content(chunk_size=8192):
                            webm_file.write(chunk)
                    print("Webm video file downloaded successfully.")
                else:
                    print("Failed to download webm file:", response.status_code)
            else:
                print("Webm video file already exists.")

            print("Converting webm file to mp3 file...")
            with VideoFileClip(webm_file_path) as video:
                with video.audio as audio:
                    audio.write_audiofile(mp3_file_path)
            os.remove(webm_file_path)
            print("Conversion to mp3 completed, webm file removed.")

            print("Adding metadata to MP3 file.")
            show_name = " ".join(URL.split("/")[-1].split("-")).title()
            audio = EasyID3(mp3_file_path)
            audio['artist'] = ', '.join(info.get('guest_names', 'Unknown guests'))
            audio['album'] = show_name
            audio['title'] = f"{date}: {info.get('info_text', 'Unknown Episode')}"
            audio.save()
            print("Metadata added successfully.")
        else:
            print(f"The episode of the {date} has already been downloaded and converted to mp3.")

if __name__ == "__main__":
    print("Visiting ZDF Mediathek...")
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run Chrome in headless mode.
    chrome_options.add_argument('--no-sandbox')  # Disable sandbox for headless mode.
    chrome_options.add_argument('--log-level=3')  # Set log level to suppress unnecessary logs.

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url=URL)
    popup_acceptor(driver)
    try:
        recent_episodes = scan_episodes(driver)
    except NoSuchElementException:
        print("The webdriver encountered an issue. Please retry.")
    selected_episodes = episode_picker(recent_episodes)
    driver.quit()

    downloadable_episodes = add_episode_urls(selected_episodes)
    download_episodes(downloadable_episodes)
