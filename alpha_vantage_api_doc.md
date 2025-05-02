Alpha Vantage API Documentation

Our stock APIs © are grouped into eight categories: (1) Core Time Series Stock Data APIs, (2) US Options Data APIs, (3) Alpha Intelligence™, (4) Fundamental Data, (5) Physical and Digital/Crypto Currencies (e.g., Bitcoin), (6) Commodities, (7) Economic Indicators, and (8) Technical Indicators - also outlined here. Examples in this documentation are for demo purposes. Claim your free API key today to explore our full API offerings!

Time Series Stock Data APIs

This suite of APIs provide global equity data in 4 different temporal resolutions: (1) daily, (2) weekly, (3) monthly, and (4) intraday, with 20+ years of historical depth. A lightweight ticker quote endpoint and several utility functions such as ticker search and market open/closure status are also included for your convenience.


TIME_SERIES_INTRADAY Trending

This API returns current and 20+ years of historical intraday OHLCV time series of the equity specified, covering pre-market and post-market hours where applicable (e.g., 4:00am to 8:00pm Eastern Time for the US market). You can query both raw (as-traded) and split/dividend-adjusted intraday data from this endpoint. The OHLCV data is sometimes called "candles" in finance literature.


API Parameters

❚ Required: function

The time series of your choice. In this case, function=TIME_SERIES_INTRADAY

❚ Required: symbol

The name of the equity of your choice. For example: symbol=IBM

❚ Required: interval

Time interval between two consecutive data points in the time series. The following values are supported: 1min, 5min, 15min, 30min, 60min

❚ Optional: adjusted

By default, adjusted=true and the output time series is adjusted by historical split and dividend events. Set adjusted=false to query raw (as-traded) intraday values.

❚ Optional: extended_hours

By default, extended_hours=true and the output time series will include both the regular trading hours and the extended (pre-market and post-market) trading hours (4:00am to 8:00pm Eastern Time for the US market). Set extended_hours=false to query regular trading hours (9:30am to 4:00pm US Eastern Time) only.

❚ Optional: month

By default, this parameter is not set and the API will return intraday data for the most recent days of trading. You can use the month parameter (in YYYY-MM format) to query a specific month in history. For example, month=2009-01. Any month in the last 20+ years since 2000-01 (January 2000) is supported.

❚ Optional: outputsize

By default, outputsize=compact. Strings compact and full are accepted with the following specifications: compact returns only the latest 100 data points in the intraday time series; full returns trailing 30 days of the most recent intraday data if the month parameter (see above) is not specified, or the full intraday data for a specific month in history if the month parameter is specified. The "compact" option is recommended if you would like to reduce the data size of each API call.

❚ Optional: datatype

By default, datatype=json. Strings json and csv are accepted with the following specifications: json returns the intraday time series in JSON format; csv returns the time series as a CSV (comma separated value) file.

❚ Required: apikey

Your API key. Claim your free API key here.


Examples (click for JSON output)

The API will return the most recent 100 intraday OHLCV bars by default when the outputsize parameter is not set
https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo

Query the most recent full 30 days of intraday data by setting outputsize=full
https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&outputsize=full&apikey=demo

Query intraday data for a given month in history (e.g., 2009-01). Any month in the last 20+ years (since 2000-01) is supported
https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&month=2009-01&outputsize=full&apikey=demo

Downloadable CSV file:
https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo&datatype=csv


💡 Tip: the intraday data (including 20+ years of historical data) is updated at the end of each trading day for all users by default. If you would like to access realtime or 15-minute delayed intraday data, please subscribe to a premium membership plan for your personal use. For commercial use, please contact sales.

* Realtime and 15-minute delayed US market data is regulated by the stock exchanges, FINRA, and the SEC. Learn more about the key market data policies you need to know as a data consumer.


Language-specific guides

Python  NodeJS  PHP  C#/.NET  Other
import requests

# replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo'
r = requests.get(url)
data = r.json()

print(data)


TIME_SERIES_DAILY

This API returns raw (as-traded) daily time series (date, daily open, daily high, daily low, daily close, daily volume) of the global equity specified, covering 20+ years of historical data. The OHLCV data is sometimes called "candles" in finance literature. If you are also interested in split/dividend-adjusted data, please use the Daily Adjusted API, which covers adjusted close values and historical split and dividend events.


API Parameters

❚ Required: function

The time series of your choice. In this case, function=TIME_SERIES_DAILY

❚ Required: symbol

The name of the equity of your choice. For example: symbol=IBM

❚ Optional: outputsize

By default, outputsize=compact. Strings compact and full are accepted with the following specifications: compact returns only the latest 100 data points; full returns the full-length time series of 20+ years of historical data. The "compact" option is recommended if you would like to reduce the data size of each API call.

❚ Optional: datatype

By default, datatype=json. Strings json and csv are accepted with the following specifications: json returns the daily time series in JSON format; csv returns the time series as a CSV (comma separated value) file.

❚ Required: apikey

Your API key. Claim your free API key here.


Examples (click for JSON output)

Sample ticker traded in the United States
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=demo

https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&outputsize=full&apikey=demo

Sample ticker traded in UK - London Stock Exchange
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=TSCO.LON&outputsize=full&apikey=demo

Sample ticker traded in Canada - Toronto Stock Exchange
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=SHOP.TRT&outputsize=full&apikey=demo

Sample ticker traded in Canada - Toronto Venture Exchange
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=GPV.TRV&outputsize=full&apikey=demo

Sample ticker traded in Germany - XETRA
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=MBG.DEX&outputsize=full&apikey=demo

Sample ticker traded in India - BSE
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=RELIANCE.BSE&outputsize=full&apikey=demo

Sample ticker traded in China - Shanghai Stock Exchange
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=600104.SHH&outputsize=full&apikey=demo

Sample ticker traded in China - Shenzhen Stock Exchange
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=000002.SHZ&outputsize=full&apikey=demo

The above is just a small sample of the 100,000+ symbols we support. Please refer to our Search Endpoint to look up any supported global stock, ETF, or mutual fund symbols of your interest.


Downloadable CSV file:
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=demo&datatype=csv



Language-specific guides

Python  NodeJS  PHP  C#/.NET  Other
import requests

# replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=demo'
r = requests.get(url)
data = r.json()

print(data)


TIME_SERIES_DAILY_ADJUSTED Trending Premium

This API returns raw (as-traded) daily open/high/low/close/volume values, adjusted close values, and historical split/dividend events of the global equity specified, covering 20+ years of historical data. The OHLCV data is sometimes called "candles" in finance literature.


API Parameters

❚ Required: function

The time series of your choice. In this case, function=TIME_SERIES_DAILY_ADJUSTED

❚ Required: symbol

The name of the equity of your choice. For example: symbol=IBM

❚ Optional: outputsize

By default, outputsize=compact. Strings compact and full are accepted with the following specifications: compact returns only the latest 100 data points; full returns the full-length time series of 20+ years of historical data. The "compact" option is recommended if you would like to reduce the data size of each API call.

❚ Optional: datatype

By default, datatype=json. Strings json and csv are accepted with the following specifications: json returns the daily time series in JSON format; csv returns the time series as a CSV (comma separated value) file.

❚ Required: apikey

Your API key. Claim your free API key here.


Examples (click for JSON output)

Sample ticker traded in the United States
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&apikey=demo

https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&outputsize=full&apikey=demo

Sample ticker traded in UK - London Stock Exchange
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=TSCO.LON&outputsize=full&apikey=demo

Sample ticker traded in Canada - Toronto Stock Exchange
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=SHOP.TRT&outputsize=full&apikey=demo

Sample ticker traded in Canada - Toronto Venture Exchange
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=GPV.TRV&outputsize=full&apikey=demo

Sample ticker traded in Germany - XETRA
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=MBG.DEX&outputsize=full&apikey=demo

Sample ticker traded in India - BSE
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=RELIANCE.BSE&outputsize=full&apikey=demo

Sample ticker traded in China - Shanghai Stock Exchange
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=600104.SHH&outputsize=full&apikey=demo

Sample ticker traded in China - Shenzhen Stock Exchange
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=000002.SHZ&outputsize=full&apikey=demo

The above is just a small sample of the 100,000+ symbols we support. Please refer to our Search Endpoint to look up any supported global stock, ETF, or mutual fund symbols of your interest.


Downloadable CSV file:
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&apikey=demo&datatype=csv


💡 Tip: this is a premium API function. Subscribe to a premium membership plan to instantly unlock all premium APIs.


Language-specific guides

Python  NodeJS  PHP  C#/.NET  Other
import requests

# replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&apikey=demo'
r = requests.get(url)
data = r.json()

print(data)

TIME_SERIES_WEEKLY

This API returns weekly time series (last trading day of each week, weekly open, weekly high, weekly low, weekly close, weekly volume) of the global equity specified, covering 20+ years of historical data.


API Parameters

❚ Required: function

The time series of your choice. In this case, function=TIME_SERIES_WEEKLY

❚ Required: symbol

The name of the equity of your choice. For example: symbol=IBM

❚ Optional: datatype

By default, datatype=json. Strings json and csv are accepted with the following specifications: json returns the weekly time series in JSON format; csv returns the time series as a CSV (comma separated value) file.

❚ Required: apikey

Your API key. Claim your free API key here.


Example (click for JSON output)

https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol=IBM&apikey=demo

https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol=TSCO.LON&apikey=demo

Downloadable CSV file:
https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol=IBM&apikey=demo&datatype=csv


Language-specific guides

Python  NodeJS  PHP  C#/.NET  Other
import requests

# replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol=IBM&apikey=demo'
r = requests.get(url)
data = r.json()

print(data)

TIME_SERIES_WEEKLY_ADJUSTED

This API returns weekly adjusted time series (last trading day of each week, weekly open, weekly high, weekly low, weekly close, weekly adjusted close, weekly volume, weekly dividend) of the global equity specified, covering 20+ years of historical data.


API Parameters

❚ Required: function

The time series of your choice. In this case, function=TIME_SERIES_WEEKLY_ADJUSTED

❚ Required: symbol

The name of the equity of your choice. For example: symbol=IBM

❚ Optional: datatype

By default, datatype=json. Strings json and csv are accepted with the following specifications: json returns the weekly time series in JSON format; csv returns the time series as a CSV (comma separated value) file.

❚ Required: apikey

Your API key. Claim your free API key here.


Example (click for JSON output)

https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol=IBM&apikey=demo

https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol=TSCO.LON&apikey=demo

Downloadable CSV file:
https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol=IBM&apikey=demo&datatype=csv


Language-specific guides

Python  NodeJS  PHP  C#/.NET  Other
import requests

# replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol=IBM&apikey=demo'
r = requests.get(url)
data = r.json()

print(data)

TIME_SERIES_MONTHLY

This API returns monthly time series (last trading day of each month, monthly open, monthly high, monthly low, monthly close, monthly volume) of the global equity specified, covering 20+ years of historical data.


API Parameters

❚ Required: function

The time series of your choice. In this case, function=TIME_SERIES_MONTHLY

❚ Required: symbol

The name of the equity of your choice. For example: symbol=IBM

❚ Optional: datatype

By default, datatype=json. Strings json and csv are accepted with the following specifications: json returns the monthly time series in JSON format; csv returns the time series as a CSV (comma separated value) file.

❚ Required: apikey

Your API key. Claim your free API key here.


Example (click for JSON output)

https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol=IBM&apikey=demo

https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol=TSCO.LON&apikey=demo

Downloadable CSV file:
https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol=IBM&apikey=demo&datatype=csv


Language-specific guides

Python  NodeJS  PHP  C#/.NET  Other
import requests

# replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol=IBM&apikey=demo'
r = requests.get(url)
data = r.json()

print(data)

TIME_SERIES_MONTHLY_ADJUSTED

This API returns monthly adjusted time series (last trading day of each month, monthly open, monthly high, monthly low, monthly close, monthly adjusted close, monthly volume, monthly dividend) of the equity specified, covering 20+ years of historical data.


API Parameters

❚ Required: function

The time series of your choice. In this case, function=TIME_SERIES_MONTHLY_ADJUSTED

❚ Required: symbol

The name of the equity of your choice. For example: symbol=IBM

❚ Optional: datatype

By default, datatype=json. Strings json and csv are accepted with the following specifications: json returns the monthly time series in JSON format; csv returns the time series as a CSV (comma separated value) file.

❚ Required: apikey

Your API key. Claim your free API key here.


Example (click for JSON output)

https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY_ADJUSTED&symbol=IBM&apikey=demo

https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY_ADJUSTED&symbol=TSCO.LON&apikey=demo

Downloadable CSV file:
https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY_ADJUSTED&symbol=IBM&apikey=demo&datatype=csv


Language-specific guides

Python  NodeJS  PHP  C#/.NET  Other
import requests

# replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY_ADJUSTED&symbol=IBM&apikey=demo'
r = requests.get(url)
data = r.json()

print(data)

Quote Endpoint Trending

This endpoint returns the latest price and volume information for a ticker of your choice. You can specify one ticker per API request.

If you would like to query a large universe of tickers in bulk, you may want to try out our Realtime Bulk Quotes API, which accepts up to 100 tickers per API request.


API Parameters

❚ Required: function

The API function of your choice.

❚ Required: symbol

The symbol of the global ticker of your choice. For example: symbol=IBM.

❚ Optional: datatype

By default, datatype=json. Strings json and csv are accepted with the following specifications: json returns the quote data in JSON format; csv returns the quote data as a CSV (comma separated value) file.

❚ Required: apikey

Your API key. Claim your free API key here.


Examples (click for JSON output)

https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey=demo

https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=300135.SHZ&apikey=demo

Downloadable CSV file:
https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey=demo&datatype=csv


💡 Tip: by default, the quote endpoint is updated at the end of each trading day for all users. If you would like to access realtime or 15-minute delayed stock quote data for the US market, please subscribe to a premium membership plan for your personal use. For commercial use, please contact sales.

* Realtime and 15-minute delayed US market data is regulated by the stock exchanges, FINRA, and the SEC. Learn more about the key market data policies you need to know as a data consumer.


Language-specific guides

Python  NodeJS  PHP  C#/.NET  Other
import requests

# replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
url = 'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey=demo'
r = requests.get(url)
data = r.json()

print(data)


Realtime Bulk Quotes Premium

This API returns realtime quotes for US-traded symbols in bulk, accepting up to 100 symbols per API request and covering both regular and extended (pre-market and post-market) trading hours. You can use this endpoint as a high-throughput alternative to the Global Quote API, which accepts one symbol per API request.


API Parameters

❚ Required: function

The time series of your choice. In this case, function=REALTIME_BULK_QUOTES

❚ Required: symbol

Up to 100 symbols separated by comma. For example: symbol=MSFT,AAPL,IBM. If more than 100 symbols are provided, only the first 100 symbols will be honored as part of the API input.

❚ Optional: datatype

By default, datatype=json. Strings json and csv are accepted with the following specifications: json returns the search results in JSON format; csv returns the search results as a CSV (comma separated value) file.

❚ Required: apikey

Your API key. Claim your free API key here.


Examples (click for JSON output)

https://www.alphavantage.co/query?function=REALTIME_BULK_QUOTES&symbol=MSFT,AAPL,IBM&apikey=demo


💡 Tip: this is a premium API function. Please subscribe to any premium membership plan that mentions "Realtime US Market Data" in its description to unlock this endpoint for your personal use. For commercial use, please contact sales.


Language-specific guides

Python  NodeJS  PHP  C#/.NET  Other
import requests

# replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
url = 'https://www.alphavantage.co/query?function=REALTIME_BULK_QUOTES&symbol=MSFT,AAPL,IBM&apikey=demo'
r = requests.get(url)
data = r.json()

print(data)
