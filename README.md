# Clinical Trial Focus Analyzer

A tool to analyze pharmaceutical companies' clinical trial data, stock price correlations, and generate insights about their research focus using AI.

## Overview

This application allows users to:
1. Enter a stock ticker for a pharmaceutical company
2. Select a date range to filter clinical trials
3. Retrieve clinical trials from ClinicalTrials.gov
4. Generate an AI-powered analysis of the company's research focus using Google Gemini
5. Visualize stock price movements in relation to clinical trial events
6. Generate AI-powered analysis of the correlation between trial events and stock performance

## Features

- **Ticker to Sponsor Mapping**: Converts stock ticker symbols to company names
- **Clinical Trial Retrieval**: Fetches trial data from ClinicalTrials.gov API
- **AI Analysis**: Uses Google Gemini to analyze and summarize research trends
- **Data Visualization**: Displays trial data in tabular format
- **Stock Price Analysis**: Shows stock prices with clinical trial events marked
- **Correlation Analysis**: Analyzes the relationship between trial events and stock movements
- **Data Export**: Download clinical trial and stock data as CSV

## Project Structure

- `simplified_app.py`: Main Streamlit application
- `data_module.py`: Functions for ticker mapping and clinical trial data retrieval
- `llm_module.py`: Functions for interacting with Google Gemini API
- `ticker_to_sponsor.json`: Mapping of stock tickers to company names

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
4. View the AI-generated analysis and raw trial data
5. Go to the "Stock Price Analysis" tab to see stock movements with trial events
6. Click "Generate AI Correlation Analysis" to get insights on trial-stock correlations

## Example

Try with ticker "LLY" (Eli Lilly) with date range 2020-2024 to see an analysis of their recent clinical research focus and the correlation with their stock performance.

## Troubleshooting

- **API Key Issues**: If you see errors about the Gemini API key, make sure it's correctly set in your `.env` file
- **Missing Data**: Some tickers may not have sufficient clinical trial data in the selected range
- **Screen Resets**: If the app resets when generating analysis, try a shorter date range with fewer trials

## Limitations

- Limited to publicly available clinical trial data
- Analysis quality depends on the available trial information
- Some ticker symbols may not be mapped to sponsor names
- Stock correlation analysis is for educational purposes only

## Disclaimer

This tool provides research insights for informational purposes only. It should not be used for investment decisions or medical advice. 