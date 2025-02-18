import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

import diskcache  # Import diskcache for persistent caching

# Initialize cache
cache = diskcache.Cache('cache') 
def setup_selenium(headless=True):
    """Sets up the Selenium WebDriver with optional headless mode."""
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def perform_search(driver, base_url, search_query):
    """Performs the search on the website using Selenium."""
    driver.get(base_url)
    try:
        # Wait for the search box to appear
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "search"))  # Adjust selector if needed
        )
        search_box.clear()
        search_box.send_keys(search_query)
        search_box.submit()
        print("Search submitted.")

        # Wait for search results to load by waiting for a specific element
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))  # Adjust selector
        )
    except Exception as e:
        print(f"Error finding or interacting with the search box: {e}")
        return None

    final_url = driver.current_url
    print(f"Redirected to: {final_url}")
    return final_url


def extract_torrent_links(driver):
    """Extract torrent links, seeders, and leechers using Selenium."""
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))  # Adjust selector
    )
    soup = BeautifulSoup(driver.page_source, "html.parser")
    torrents = []
    for row in soup.select("table tbody tr"):
        try:
            title = row.select_one(".coll-1.name a:nth-of-type(2)").text.strip()
            seeders = int(row.select_one(".coll-2").text.strip())
            leechers = int(row.select_one(".coll-3").text.strip())
            link = row.select("a")[1]["href"]
            torrents.append({"title": title, "seeders": seeders, "leechers": leechers, "link": link})
        except (AttributeError, ValueError):
            continue
    return torrents


def extract_magnet_link(driver):
    """Extract the magnet link from the torrent details page."""
    try:
        magnet_link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href^="magnet:"]'))
        )
        return magnet_link.get_attribute("href")
    except Exception as e:
        print(f"Error extracting magnet link: {e}")
        return None


# def save_magnet_link(search_query, magnet_link):
#     """Saves the magnet link to a file."""
#     if not magnet_link:
#         print("No magnet link found.")
#         return

#     directory = "magnet_links"
#     os.makedirs(directory, exist_ok=True)
#     file_path = os.path.join(directory, f"{search_query}.txt")

#     with open(file_path, "w") as file:
#         file.write(magnet_link + "\n")

#     print(f"Magnet link saved to {file_path}")


def fetch_magnet_links(search_query, base_url="https://1337x-to-1.pages.dev/", return_all=False, season_number=None):
    """Main function to fetch magnet links using Selenium with persistent caching."""
    
    # Check cache first
    cached_magnet_link = cache.get(search_query)  # Check if result is already cached
    if cached_magnet_link:
        print("Returning cached magnet link.")
        return cached_magnet_link

    driver = setup_selenium(headless=True)
    try:
        # Step 1: Perform search and navigate to results
        final_url = perform_search(driver, base_url, search_query)
        if not final_url:
            return None if not return_all else []

        # Step 2: Extract torrent links and filter by season if provided
        torrents = extract_torrent_links(driver)
        if not torrents:
            print("No torrents found.")
            return None if not return_all else []

        if season_number:
            # Filter torrents to include only those mentioning the correct season
            season_keyword = f"Season {season_number}"
            torrents = [torrent for torrent in torrents if season_keyword in torrent["title"]]

            if not torrents:
                print(f"No torrents found for {season_keyword}.")
                return None if not return_all else []

        if return_all:
            return [
                {
                    "title": torrent["title"],
                    "link": torrent["link"],
                    "seeders": torrent["seeders"]
                }
                for torrent in torrents
            ]

        # Select the torrent with the highest seeders
        best_torrent = max(torrents, key=lambda x: x["seeders"])
        print(f"Selected torrent: {best_torrent['title']} with {best_torrent['seeders']} seeders.")

        # Step 3: Navigate to the selected torrent's detail page
        detail_page_url = "https:" + best_torrent["link"]
        driver.get(detail_page_url)

        # Explicitly wait for the magnet link to appear
        magnet_link = extract_magnet_link(driver)
        if magnet_link:
            print(f"Magnet link: {magnet_link}")
        else:
            print("No magnet link found on the page.")
        
        # Cache the result for future use
        cache.set(search_query, magnet_link, expire=864000)  # Cache for 24 hours (86400 seconds)

        return magnet_link
    finally:
        driver.quit()





if __name__ == "__main__":
    start_time = time.time()  # Record the start time

    query = input("Enter your search query: ").strip()
    magnet_link = fetch_magnet_links(query)

    end_time = time.time()  # Record the end time
    total_time = end_time - start_time  # Calculate total elapsed time

    if magnet_link:
        print("Magnet link retrieved successfully.")
    else:
        print("Failed to retrieve magnet link.")

    print(f"Total execution time: {total_time:.2f} seconds")
