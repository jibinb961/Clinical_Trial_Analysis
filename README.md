# Clinical Trial Analyzer

A Streamlit application that retrieves and analyzes clinical trials from ClinicalTrials.gov, with AI-powered insights generation using Gemini AI. The app now includes financial analysis of biotech companies sponsoring the trials.

## Features

### Core Features
- Search for clinical trials by keyword
- Retrieve details for multiple studies (up to 1,000)
- Extract key information from each trial:
  - NCT ID
  - Title
  - Phase
  - Enrollment count
  - Conditions
  - Interventions
  - Sponsor
  - Primary outcome
  - Brief summary
- Generate AI analysis of trial trends
- Download results as CSV

### Financial Analysis Features
- Map trial sponsors to public biotech companies and their stock tickers
- Display stock performance metrics:
  - 90-day price and volume data 
  - Moving averages (7-day, 30-day)
  - Daily returns
- Generate AI analysis of potential market impact
- Visual stock charts with trial event markers
- Watchlist functionality for recurring sponsors
- Export financial metrics alongside trial data

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install required packages:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

1. Run the application:
   ```
   streamlit run app.py
   ```
2. Enter a search term (e.g., "diabetes", "cancer", "covid")
3. Specify the number of studies to retrieve
4. Click "Search and Analyze"
5. Review the results, including:
   - AI-generated insights
   - Detailed trial information
   - Financial analysis for public companies
   - Stock performance metrics and charts
6. Use the "Show Financial Impact" option to focus on trials from public companies
7. Add companies to your watchlist for future reference
8. Download the analysis as CSV

## Technical Details

The application uses:
- Streamlit for the user interface
- ClinicalTrials.gov API for retrieving trial data
- Google's Gemini AI for generating insights
- yfinance for retrieving stock data
- Matplotlib for generating stock charts
- Pandas for data manipulation

## Project Structure

- `app.py`: Main application code
- `finance_module.py`: Financial analysis functions
- `company_name_to_ticker.json`: Mapping of company names to stock tickers
- `requirements.txt`: Required Python packages
- `.env`: Environment variables (not included in repository)

## Limitations

- The ClinicalTrials.gov API has a limit of retrieving 10,000 studies
- Only a subset of biotech companies are mapped to stock tickers
- Financial analysis is performed on-demand, which may cause slight delays
- Stock data is retrieved from Yahoo Finance with standard limitations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 