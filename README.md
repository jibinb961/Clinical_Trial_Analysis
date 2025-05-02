# Clinical Trial Stock Correlation Analyzer

A comprehensive tool to analyze pharmaceutical companies' clinical trial data, stock price correlations, and generate AI-powered insights about research focus and market impact.

## Overview

This application allows users to:
1. Enter a stock ticker for a pharmaceutical company
2. Select a date range to filter clinical trials
3. Retrieve clinical trials from ClinicalTrials.gov
4. Generate an AI-powered analysis of the company's research focus using Google Gemini
5. Visualize stock price movements in relation to clinical trial events
6. Generate AI-powered analysis of the correlation between trial events and stock performance

## Key Features

- **Clinical Trial Analysis**: 
  - Fetches trial data from ClinicalTrials.gov API v2
  - Maps stock tickers to pharmaceutical company names
  - AI-powered analysis of research focus areas and pipeline
  - Handles various date formats and structures from the API

- **Stock Price Correlation**:
  - Visualizes stock prices with clinical trial events marked
  - Uses a 15-day window before and after trial start dates to analyze market impact
  - AI-generated correlation analysis between trial announcements and stock movements
  - Identifies trials with significant market impact

- **Data Visualization & Export**:
  - Interactive stock price charts with trial events marked
  - Tabular trial data with sorting options
  - Timeline view of ongoing clinical trials
  - Export functionality for both trial and stock data

## Project Structure

- `simplified_app.py`: Main Streamlit application with UI and visualization logic
- `data_module.py`: Functions for ticker mapping and clinical trial data retrieval
- `llm_module.py`: Integration with Google Gemini AI for analysis generation
- `ticker_to_sponsor.json`: Mapping of stock tickers to company names
- `example.env`: Template for setting up the environment variables

## Technical Improvements

- **Robust Date Handling**: Properly processes various date formats (year, year-month, full dates)
- **Enhanced State Management**: Prevents UI resets during analysis generation
- **Error Handling**: Comprehensive error handling for API calls and data processing
- **Performance Optimization**: 
  - Efficient data fetching with pagination support
  - Client-side filtering for faster results
  - Streamlined UI with optimized state updates

## Requirements

- Python 3.8+
- Streamlit
- Pandas
- yfinance
- Google GenerativeAI Python SDK
- python-dotenv
- requests
- matplotlib

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. **Set up your Google Gemini API key:**
   - Get an API key from https://aistudio.google.com/app/apikey
   - Create a `.env` file in the project root directory
   - Add your API key to the file:
     ```
     GEMINI_API_KEY=your_actual_api_key_here
     ```
   - Alternatively, set it as an environment variable in your terminal:
     ```
     export GEMINI_API_KEY=your_actual_api_key_here
     ```
4. Run the application:
   ```
   streamlit run simplified_app.py
   ```

## Usage

1. Enter a pharmaceutical company ticker (e.g., "PFE" for Pfizer)
2. Select start and end dates to filter trials
3. Click "Analyze Sponsor Focus"
4. View the AI-generated analysis and detailed trial data in the tabs
5. Scroll down to the Stock Price Analysis section
6. Click "Generate Stock-Trial Correlation Analysis" to get AI insights on the correlation between trial announcements and stock movements

## Example Use Cases

- **Investment Research**: Analyze how clinical trial announcements impact stock performance
- **Pharmaceutical Industry Analysis**: Identify research trends and focus areas of companies
- **Competitor Analysis**: Compare trial portfolios and market reactions across companies
- **Market Impact Assessment**: Measure the impact of different trial types and phases on stock prices

## Troubleshooting

- **API Key Issues**: If you see errors about the Gemini API key, make sure it's correctly set in your `.env` file
- **Missing Data**: Some tickers may not have sufficient clinical trial data in the selected range
- **Date Ranges**: For optimal performance, use a date range of 2-3 years when analyzing larger companies

## Limitations

- Limited to publicly available clinical trial data from ClinicalTrials.gov
- Analysis quality depends on the completeness of trial information
- Some ticker symbols may not be mapped to sponsor names
- Stock correlation analysis uses a 15-day window which may not capture longer-term effects
- Stock price movements are influenced by many factors beyond clinical trials

## Disclaimer

This tool provides research insights for informational purposes only. It should not be used for investment decisions or medical advice. The stock correlation analysis does not constitute financial advice or recommendations. 