import pandas as pd
import requests

def get_all_nse_tickers():
    """
    Downloads complete NSE equity list and formats for yfinance.
    Returns a DataFrame with Symbol, Company Name, Sector.
    """

    # NSE provides this CSV publicly
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

    headers = {
        "User-Agent": "Mozilla/5.0"  # Required to avoid request block
    }

    print("Fetching NSE ticker list...")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch. Status: {response.status_code}")
        return None

    # Read CSV
    from io import StringIO
    df = pd.read_csv(StringIO(response.text))

    # Clean column names
    df.columns = df.columns.str.strip()

    # Add yfinance format
    df["YF_Ticker"] = df["SYMBOL"].str.strip() + ".NS"

    # Keep useful columns
    result = df[["SYMBOL", "NAME OF COMPANY", "YF_Ticker"]].copy()
    result.columns = ["NSE_Symbol", "Company_Name", "YF_Ticker"]

    print(f"Total tickers fetched: {len(result)}")
    return result


# Run it
tickers_df = get_all_nse_tickers()

if tickers_df is not None:
    # Save to CSV
    tickers_df.to_csv("nse_all_tickers.csv", index=False)
    print("Saved to nse_all_tickers.csv")
    print(tickers_df.head(20))  # Preview first 