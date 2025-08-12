# test_scraper.py
import os
import pandas as pd
from dotenv import load_dotenv
from gemini import interpret_command_with_gemini, run_single_scrape  # your main scraper file

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print(" GEMINI_API_KEY not found in .env file.")
    exit()

def run_test(test_name, command):
    print(f"\n=== Running test: {test_name} ===")
    try:
        filters = interpret_command_with_gemini(command, GEMINI_API_KEY)
        results = run_single_scrape(filters)

        # Check structure
        if not isinstance(results, list):
            print(f" FAIL: Results are not a list.")
            return False, []
        if results and any(not isinstance(r, dict) for r in results):
            print(f" FAIL: Some rows are not dictionaries.")
            return False, []
        expected_keys = {"Action", "State", "Name", "Farm", "Phone", "Website"}
        if results and not expected_keys.issubset(results[0].keys()):
            print(f" FAIL: Missing expected keys in first result.")
            return False, []

        # If all checks pass
        print(f" PASS: Scraped {len(results)} rows for '{test_name}'")
        return True, results

    except Exception as e:
        print(f" FAIL: Exception occurred in '{test_name}' -> {e}")
        return False, []

if __name__ == "__main__":
    test_cases = [
        ("Single State Search", "find member in Oklahoma"),
        ("Multiple States Search", "find member in Kansas and Texas"),
        ("Specific Breed Search", "find American Red breed in Kansas"),
        ("State + Member Type", "find Dwight Elmore in Kansas"),
        ("Nonsense Query", "find cats in Indonesia"),
    ]

    results_summary = []
    all_results = []

    for name, command in test_cases:
        passed, results = run_test(name, command)
        # Add metadata to results for easier trace
        for r in results:
            r["Test Case"] = name
        all_results.extend(results)
        results_summary.append((name, passed))

    # Save all results to CSV
    if all_results:
        df = pd.DataFrame(all_results)
        df.to_csv("test_scrape_results.csv", index=False)
        print(f"\n All scraped results saved to test_scrape_results.csv ({len(df)} rows).")
    else:
        print("\n No results scraped for any test case.")

    # Print test summary
    print("\n=== Test Summary ===")
    for name, passed in results_summary:
        status = "PASS" if passed else "FAIL"
        print(f"{name}: {status}")
