# Alpha Vantage API Test Scripts

These scripts demonstrate how to use the Alpha Vantage API to fetch stock data and replace the yfinance library in the DrugAnalysis project.

## Prerequisites

- Python 3.6 or higher
- Required packages: `requests`, `pandas`, `matplotlib`
- Alpha Vantage API key

## Setup

1. Install the required packages:

```bash
pip install requests pandas matplotlib
```

2. Set up your Alpha Vantage API key:

You can either:
- Set it as an environment variable:
  ```bash
  # Linux/macOS
  export ALPHA_VANTAGE_API_KEY="your_api_key_here"
  
  # Windows (Command Prompt)
  set ALPHA_VANTAGE_API_KEY=your_api_key_here
  
  # Windows (PowerShell)
  $env:ALPHA_VANTAGE_API_KEY="your_api_key_here"
  ```
- Or update the scripts directly by replacing `"your_api_key_here"` with your actual API key

3. Get your Alpha Vantage API key:
   - Sign up at [Alpha Vantage](https://www.alphavantage.co/support/#api-key)
   - The free tier allows 5 API calls per minute and 500 calls per day

## Test Scripts

### 1. alpha_vantage_test.py

This script demonstrates basic usage of the Alpha Vantage API to fetch:
- Daily stock data
- Company overview information

It tests with three popular stocks (AAPL, MSFT, GOOG) and generates stock price charts.

```bash
python alpha_vantage_test.py
```

### 2. alpha_vantage_finance_module_test.py

This script is specifically designed to demonstrate how to replace yfinance with Alpha Vantage in the finance_module.py file. It:
- Fetches stock data in a format compatible with the existing code
- Creates charts similar to those in the finance_module.py
- Implements error handling and API rate limiting

```bash
python alpha_vantage_finance_module_test.py
```

## Key Functions

### fetch_stock_data(ticker, days=90)

This function fetches historical stock data for a given ticker:
- `ticker`: The stock symbol (e.g., "AAPL")
- `days`: Number of days of historical data to retrieve (default: 90)

The function returns a pandas DataFrame with the following columns:
- Open: Opening price
- High: Highest price during the day
- Low: Lowest price during the day
- Close: Closing price
- Adj Close: Adjusted closing price
- Volume: Trading volume

Example usage:
```python
import alpha_vantage_finance_module_test as av

# Fetch 90 days of Apple stock data
df = av.fetch_stock_data("AAPL", 90)
print(df.tail())
```

### generate_stock_price_chart(ticker, days=90, save_figure=False)

This function generates a stock price chart:
- `ticker`: The stock symbol
- `days`: Number of days of historical data to display
- `save_figure`: Whether to save the chart as a PNG file

Example usage:
```python
import alpha_vantage_finance_module_test as av
import matplotlib.pyplot as plt

# Generate and display a chart for Microsoft
fig = av.generate_stock_price_chart("MSFT", 90, save_figure=True)
plt.show()
```

## API Rate Limits

The free tier of Alpha Vantage API has the following limits:
- 5 API calls per minute
- 500 API calls per day

Both test scripts implement a 15-second delay between API calls to respect these limits.

## Alpha Vantage vs. yfinance

Alpha Vantage provides several advantages over yfinance:
- More reliable data source
- Official API with documentation
- Support for a wide range of financial data

The `fetch_stock_data()` function in the test scripts is designed to return data in the same format as yfinance, making it a drop-in replacement in the finance_module.py file.

## Further Resources

- [Alpha Vantage Documentation](https://www.alphavantage.co/documentation/)
- [Alpha Vantage API Parameters](https://www.alphavantage.co/documentation/#time-series-data)
- [Python requests Library](https://docs.python-requests.org/en/latest/)
- [Pandas Documentation](https://pandas.pydata.org/docs/) 