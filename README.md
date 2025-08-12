# AMGR Web Scraper Using Gemini

This script automates data scraping from the American Meat Goat Registry (AMGR) directory search page using Selenium. It integrates Google Gemini AI to interpret natural language commands from the user (via CLI) into structured search filters (state, member, breed).

## Requirements
- Python 3.12.
- Google Gemini API Key <br> You can get it from https://aistudio.google.com/app/apikey 
- Chrome Browser Installed
- Chromedriver

## Installation
1. Clone repository
```
git clone https://github.com/Haiqelhakeem/mrscrapper-test
cd mrscrapper-test
```
2. Install dependencies
```
pip install selenium webdriver-manager beautifulsoup4 pandas python-dotenv google-generativeai
```
3. Set up environment variables:
Create a .env file in the project root:
```
GEMINI_API_KEY=your_google_gemini_api_key_here
```
4. Verify Chrome is installed on your system. <br> The script will automatically download the matching ChromeDriver version.

## Usage
1. Run `gemini.py` to use it manually:
```
python gemini.py
```
When prompted, enter a natural language command like this format:
```
find member Dwight Elmore and Bill Carter in Kansas and Texas
```
Gemini will interpret it as:
```
{
  "state": ["Kansas", "Texas"],
  "member": ["Dwight Elmore", "Bill Carter"]
}
```
Save the data to a CSV file with format:
```
amgr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv
```

2. Run `test_scrape`.py for automated scrape:
```
python test_scrape.py
```

## Expected Output:
| Action | State | Name     | Farm        | Phone   | Website                                        |
| ------ | ----- | -------- | ----------- | ------- | ---------------------------------------------- |
|    | KS    | Dwight Elmore | 3TAC Ranch Genetics  - 3TR | (620)  899-0770 | [Website](https://www.amgr.org/frm_directorySearch.cfm) |

# Notes
Currently this project can only scrape from https://www.amgr.org/frm_directorySearch.cfm. <br>
This project is for testing purpose only.