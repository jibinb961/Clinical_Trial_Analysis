# Clinical Trial Analyzer

A Streamlit application that analyzes clinical trials data from ClinicalTrials.gov using Google's Gemini AI.

## Features

- Search for clinical trials on ClinicalTrials.gov by keyword
- Retrieve data for multiple studies at once (up to 1000)
- Extract key information including:
  - NCT ID
  - Brief Title
  - Phase
  - Enrollment (Number of Participants)
  - Conditions being studied
  - Interventions
  - Sponsor
  - Primary Outcomes
- AI-powered analysis of trends across all studies
- Display results in an interactive table
- Download results as a CSV file
- Download AI insights as a text file

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up your Gemini API key:
   - Create a `.env` file in the project root
   - Add your Gemini API key to the file:
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     ```

## Running the Application

Run the application with:

```
streamlit run app.py
```

## Usage

1. Enter a search term (e.g., "diabetes", "cancer", "covid", "remdesivir")
2. Specify the number of studies to retrieve (1-1000)
3. Click "Search and Analyze"
4. The application will:
   - Fetch clinical trial data from ClinicalTrials.gov API
   - Parse the XML responses to extract structured data
   - Generate a concise summary for each study
   - Use Gemini AI to analyze trends across all studies
   - Display the results in a table
5. Download options:
   - "Download Results as CSV" to export the structured data
   - "Download AI Analysis as Text" to save the AI-generated insights

## How It Works

1. **Data Retrieval**: Uses the ClinicalTrials.gov API to fetch XML data for clinical trials matching the search term
2. **XML Parsing**: Extracts structured information from complex XML responses using ElementTree
3. **Batch Processing**: Processes studies in batches of 100 to respect API limits
4. **AI Analysis**: Sends all study summaries to Gemini in a single call for comprehensive trend analysis
5. **Result Presentation**: Displays both the structured data and AI insights in an organized interface

## Requirements

- Python 3.7+
- Streamlit
- Pandas
- Google Generative AI Python SDK (genai)
- Requests
- python-dotenv
- xml.etree.ElementTree

## Error Handling

The application includes:
- Robust XML parsing with fallback mechanisms
- Graceful handling of missing data fields
- Retries for API requests with informative error messages
- Exponential backoff for Gemini API calls

## Notes

- The ClinicalTrials.gov API limits retrievals to 10,000 studies maximum
- Processing a large number of studies may take time due to API rate limits
- For best results, use specific search terms to narrow down the results 