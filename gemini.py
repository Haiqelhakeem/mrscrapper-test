import google.generativeai as genai  # Google Gemini API client

# Selenium & WebDriver imports for browser automation
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup   # HTML parsing
import pandas as pd             # Data handling and export
import time, json, os
from datetime import datetime   # For timestamps in logs & filenames
import itertools                # To generate combinations of filters
from dotenv import load_dotenv  # Load secrets from .env file

# Load environment variables (e.g., GEMINI_API_KEY)
load_dotenv()


# ========================
# HELPER AND LOGIC FUNCTIONS
# ========================

def interpret_command_with_gemini(command: str, api_key: str) -> dict:
    """
    Uses the Gemini API to turn a free-text user command
    into structured filter criteria for scraping.
    
    Expected output format:
    {
      "state": "Texas" or ["Texas", "Kansas"],
      "member": "Dwight Elmore" or ["Dwight Elmore", "Bill Carter"],
      "breed": "(AR) - American Red"
    }
    
    Missing keys are omitted.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    # Prompt instructs Gemini to return JSON with specific keys
    prompt = f"""
    You are an expert at interpreting scraping commands. Analyze the following user request and extract the filter criteria.
    Return the output as a JSON object with the keys "state", "member", and "breed".
    If multiple values are mentioned for ANY key, the value must be a list of strings.
    If a criterion is not mentioned, omit its key from the JSON.

    User Request: "{command}"
    """
    try:
        response = model.generate_content(prompt)  # Send prompt to Gemini
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        filters = json.loads(json_text)  # Parse JSON output
        print(f"Gemini interpretation: {filters}")
        return filters
    except Exception as e:
        # If AI parsing fails, return empty filters to allow fallback scraping
        print(f"Error interpreting command with Gemini: {e}")
        return {}


def select_by_partial_text(select_element, partial_text):
    """
    Selects a dropdown option if its text contains the given partial text (case-insensitive).
    """
    for option in select_element.options:
        if partial_text.lower() in option.text.lower():
            select_element.select_by_visible_text(option.text)
            print(f"- Selected '{option.text}'")
            return
    raise ValueError(f"No option containing '{partial_text}' found.")


def select_by_case_insensitive_text(select_element, text_to_find):
    """
    Selects a dropdown option whose text exactly matches (case-insensitive).
    """
    for option in select_element.options:
        if text_to_find.lower() == option.text.lower():
            select_element.select_by_visible_text(option.text)
            print(f"- Selected '{option.text}'")
            return
    raise ValueError(f"No option with text '{text_to_find}' found.")


def scrape_table_with_links(page_source):
    """
    Extracts table data from the HTML source.
    Also retrieves the website link if available in the last column.
    """
    soup = BeautifulSoup(page_source, 'html.parser')
    table = soup.find('table', class_='table')
    if not table:
        return []

    rows_data = []
    for row in table.find('tbody').find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 6:
            continue  # Skip malformed rows

        row_data = {
            'Action': cells[0].get_text(strip=True),
            'State': cells[1].get_text(strip=True),
            'Name': cells[2].get_text(strip=True),
            'Farm': cells[3].get_text(strip=True),
            'Phone': cells[4].get_text(strip=True),
        }

        # Extract website link if present
        website_link_tag = cells[5].find('a')
        row_data['Website'] = website_link_tag['href'] if website_link_tag else ''
        rows_data.append(row_data)

    return rows_data


def run_single_scrape(filters: dict):
    """
    Opens the AMGR search page, applies the given filters,
    scrapes all result pages, and returns the data.
    """
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    wait = WebDriverWait(driver, 10)
    url = "https://www.amgr.org/frm_directorySearch.cfm"
    driver.get(url)

    scraped_data = []
    try:
        print(f"\nApplying filters: {filters}")

        # Apply filters if provided
        if filters.get('state'):
            select_by_case_insensitive_text(
                Select(wait.until(EC.presence_of_element_located((By.NAME, "stateID")))),
                filters['state']
            )
            time.sleep(2)

        if filters.get('member'):
            select_by_case_insensitive_text(
                Select(wait.until(EC.presence_of_element_located((By.NAME, "memberID")))),
                filters['member']
            )
            time.sleep(1)

        if filters.get('breed'):
            select_by_partial_text(
                Select(wait.until(EC.presence_of_element_located((By.NAME, "breedID")))),
                filters['breed']
            )
            time.sleep(1)

        # Submit the search form
        wait.until(EC.element_to_be_clickable((By.ID, "submitButton"))).click()
        print("Form submitted. Waiting for results...")
        time.sleep(3)

        # Loop through paginated results
        page_number = 1
        while True:
            print(f"Scraping page {page_number}...")
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                page_data = scrape_table_with_links(driver.page_source)

                if not page_data:
                    break  # Stop if no rows found
                scraped_data.extend(page_data)

                # Check if there's a next page
                next_button_li = driver.find_element(By.ID, "example_next")
                if "disabled" in next_button_li.get_attribute("class"):
                    break  # No more pages

                wait.until(EC.element_to_be_clickable(
                    next_button_li.find_element(By.TAG_NAME, "a"))
                ).click()

                page_number += 1 # Increment page number after successful scrape
                time.sleep(2)
            except (NoSuchElementException, TimeoutException):
                break  # Stop on errors or no table found
    finally:
        driver.quit()
        return scraped_data


# ========================
# MAIN WORKFLOW
# ========================
def main():
    # Load API key from environment
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not found in .env file.")
        return

    # Get user command from CLI
    command = input("Enter your command (e.g., 'find member Dwight Elmore and Bill Carter in Kansas and Texas'): ")

    # Use Gemini to interpret it into filters
    filters = interpret_command_with_gemini(command, GEMINI_API_KEY)

    # Ensure all filters are lists for combination generation
    states = filters.get('state', [None])
    members = filters.get('member', [None])
    breeds = filters.get('breed', [None])
    if not isinstance(states, list): states = [states]
    if not isinstance(members, list): members = [members]
    if not isinstance(breeds, list): breeds = [breeds]

    # Create every possible combination of state/member/breed filters
    filter_combinations = list(itertools.product(states, members, breeds))

    all_results = []
    for combo in filter_combinations:
        current_filters = {}
        if combo[0] is not None: current_filters['state'] = combo[0]
        if combo[1] is not None: current_filters['member'] = combo[1]
        if combo[2] is not None: current_filters['breed'] = combo[2]

        # Skip unless it's a valid combination or a full "no filter" search
        if not current_filters and combo != (None, None, None):
            continue

        print(f"\n--- Starting scrape for combination: {current_filters} ---")
        results_for_combo = run_single_scrape(current_filters)
        if results_for_combo:
            all_results.extend(results_for_combo)

    # Save results
    if all_results:
        final_df = pd.DataFrame(all_results).drop_duplicates().reset_index(drop=True)
        filename = f"amgr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        final_df.to_csv(filename, index=False)
        print("\nScrape complete!")
        print(f"Data for {len(final_df)} unique entries saved to {filename}")
        print(final_df.head())
    else:
        print("\nNo results found across all searches.")


if __name__ == "__main__":
    main()
