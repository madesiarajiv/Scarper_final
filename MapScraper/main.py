import os
from query_manager import queries
import time
import pandas as pd
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Set up WebDriver with Chrome options
chrome_options = webdriver.ChromeOptions()

# Configure Chrome to use its default Downloads directory
prefs = {
    "download.default_directory": "",  # Leave empty for Chrome's default Downloads folder
    "download.prompt_for_download": False,
    "safebrowsing.enabled": True
}
chrome_options.add_experimental_option("prefs", prefs)


def initialize_driver():
    # Initialize the WebDriver with Chrome options
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )


# Function to search Google Maps and return results
def search_google_maps(query, max_results=10000, retries=2):
    try:
        driver = initialize_driver()
        wait = WebDriverWait(driver, 10)

        driver.get("https://www.google.com/maps")  # Open Google Maps
        wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))

        # Enter the search query automatically
        search_box = driver.find_element(By.ID, "searchboxinput")
        search_box.send_keys(query)  # Automatically enters the query into the search box
        search_box.send_keys("\n")
        time.sleep(5)

        results = []
        last_scroll_height = 0
        retry_count = 0

        while len(results) < max_results:
            # Wait for result cards to load
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.bfdHYd")))

            places = driver.find_elements(By.CSS_SELECTOR, "div.bfdHYd")
            print(f"Found {len(places)} places so far...")

            for place in places:
                try:
                    # Extract the name
                    name = place.find_element(By.CSS_SELECTOR, "div.qBF1Pd").text
                except:
                    name = "N/A"

                try:
                    # Extract the rating
                    rating = place.find_element(By.CSS_SELECTOR, "span.ZkP5Je").get_attribute("aria-label")
                    rating = rating.split(" ")[0] if rating else "N/A"
                except:
                    rating = "N/A"

                try:
                    # Extract the number of reviews
                    reviews = place.find_element(By.CSS_SELECTOR, "span.UY7F9").text
                except:
                    reviews = "N/A"

                try:
                    # Extract the category
                    category = place.find_element(By.XPATH, ".//div[contains(@class, 'W4Efsd')]/span[1]/span").text
                except:
                    category = "N/A"

                try:
                    # Extract the address
                    address = place.find_element(By.XPATH, ".//span[contains(text(), ',')]").text
                except:
                    address = "N/A"

                try:
                    # Extract the phone number
                    phone = place.find_element(By.CSS_SELECTOR, "span.UsdlK").text
                except:
                    phone = "N/A"

                # Add the area column with the area name from the query
                area = query.split(" in ")[-1]  # Extract area from the query string

                results.append({
                    "Name": name,
                    "Phone": phone,
                    "Category": category,
                    "Address": address,
                    "Reviews": reviews,
                    "Rating": rating,
                    "Area": area  # New column for Area
                })

                # Stop if we reach the maximum desired results
                if len(results) >= max_results:
                    break

            # Scroll to load more results
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)

            # Check if new data has been loaded
            new_scroll_height = driver.execute_script("return document.body.scrollHeight;")
            if new_scroll_height == last_scroll_height:
                retry_count += 1
                if retry_count > retries:  # Retry limit reached
                    print(f"Query '{query}' failed to load additional data after retries. Skipping...")
                    break
            else:
                retry_count = 0

            last_scroll_height = new_scroll_height

        return results

    except Exception as e:
        print(f"An error occurred while processing query '{query}': {e}")
        return []
    finally:
        driver.quit()


# Remove duplicates and save to a unique file
def save_unique_results(data, output_directory, base_file_name="google_maps_data_all_queries.csv"):
    if not data:
        print("No data to save.")
        return None

    # Convert data to DataFrame
    df = pd.DataFrame(data)

    # Drop duplicates based on 'Name' and 'Address'
    unique_df = df.drop_duplicates(subset=["Name", "Address"], keep="first")

    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Generate a unique file name if the base file already exists
    unique_file_name = get_unique_filename(output_directory, base_file_name)

    # Save the unique data to a CSV file
    file_path = os.path.join(output_directory, unique_file_name)
    unique_df.to_csv(file_path, index=False)

    print(f"Unique data saved to {file_path} with {len(unique_df)} records.")
    return file_path


# Function to get a unique file name if the file already exists
def get_unique_filename(directory, base_name):
    name, ext = os.path.splitext(base_name)
    counter = 1
    unique_name = base_name

    while os.path.exists(os.path.join(directory, unique_name)):
        unique_name = f"{name}_{counter}{ext}"
        counter += 1

    return unique_name





# Main function
def main():
    all_results = []  # List to hold results of all queries

    # Loop through each query in the list
    for query in queries:
        print(f"Processing query: {query}")

        # Call the search function for each query
        data = search_google_maps(query, max_results=10000)

        if data:
            # Append the data to the all_results list
            all_results.extend(data)

            print(f"Data for '{query}' processed.")
        else:
            print(f"No data was scraped for query '{query}'. Please check the script or query.")

    # After processing all queries, merge and save the data
    downloads_dir = os.path.expanduser("~/Downloads")
    save_unique_results(all_results, downloads_dir)


if __name__ == "__main__":
    main()