import streamlit as st
import pandas as pd
import os
import time
import datetime
import json
import requests
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import google.generativeai as genai
from dotenv import load_dotenv
import finance_module as fin
import matplotlib.pyplot as plt

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("Please set the GEMINI_API_KEY environment variable.")
    st.stop()

# Initialize Gemini client
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-001')

# Constants
API_V2_URL = "https://clinicaltrials.gov/api/v2/studies"
MAX_RESULTS_PER_PAGE = 100  # Maximum allowed by the API
DEFAULT_NUM_STUDIES = 10
MAX_ALLOWED_STUDIES = 1000
MAX_RETRIEVABLE_STUDIES = 10000  # API limitation: only first 10,000 studies can be retrieved

# Define simplified Pydantic model for structured Gemini responses
class ClinicalTrialInfo(BaseModel):
    nct_id: str = Field(description="The NCT ID of the clinical trial")
    brief_title: Optional[str] = Field(default="N/A", description="Brief title of the study")
    phase: Optional[str] = Field(default="N/A", description="Phase of the clinical trial (e.g., Phase I, II, III, IV)")
    enrollment: Optional[str] = Field(default="N/A", description="Number of participants in the trial")
    conditions: Optional[str] = Field(default="N/A", description="Medical conditions being studied")
    interventions: Optional[str] = Field(default="N/A", description="Interventions being tested")
    sponsor: Optional[str] = Field(default="N/A", description="Organization or institution sponsoring the trial")
    primary_outcome: Optional[str] = Field(default="N/A", description="Primary outcome of the study")
    brief_summary: Optional[str] = Field(default="N/A", description="Brief summary of the study")
    ticker: Optional[str] = Field(default=None, description="Stock ticker symbol for the sponsoring company")
    has_financial_data: Optional[bool] = Field(default=False, description="Whether financial data is available for this trial")
    market_analysis: Optional[str] = Field(default=None, description="Market impact analysis from LLM")
    investment_relevance: Optional[str] = Field(default=None, description="Investment relevance rating (Low/Medium/High)")
    
    # Time-related fields
    start_date: Optional[str] = Field(default=None, description="Start date of the clinical trial")
    primary_completion_date: Optional[str] = Field(default=None, description="Primary completion date of the trial")
    completion_date: Optional[str] = Field(default=None, description="Completion date of the trial")
    last_update_date: Optional[str] = Field(default=None, description="Last update date of the trial")
    status: Optional[str] = Field(default=None, description="Current status of the trial (e.g., Completed, Recruiting)")
    status_verified_date: Optional[str] = Field(default=None, description="Date when status was last verified")

def fetch_clinical_trials(search_params: Dict) -> Optional[Dict]:
    """
    Fetch clinical trial data from ClinicalTrials.gov API using the v2 endpoint
    with support for advanced filtering.
    
    Args:
        search_params: Dictionary containing search parameters and filters
        
    Returns:
        Dict containing the API response or None if the request failed
    """
    try:
        # Calculate current page parameters
        min_rank = search_params.get("min_rank", 1)
        max_rank = search_params.get("max_rank", 100)
        page_size = max_rank - min_rank + 1
        
        # Base parameters for the v2 API
        params = {
            "format": "json",
            "pageSize": page_size,
            "countTotal": "true"
        }
        
        # Determine search mode and add appropriate query parameters
        is_dual_search = search_params.get("is_dual_search", False)
        is_sponsor_only = search_params.get("is_sponsor_only", False)
        
        # Add query parameters based on search mode
        if is_dual_search:
            # When both disease and sponsor are provided, use advanced query syntax
            disease_term = search_params.get("disease_term", "")
            sponsor_term = search_params.get("sponsor_term", "")
            
            # Use advanced query parameter with AND logic
            params["query.adv"] = f"AREA[ConditionSearch]('{disease_term}') AND AREA[SponsorSearch]('{sponsor_term}')"
            
            st.info(f"Performing dual filter search for condition '{disease_term}' AND sponsor '{sponsor_term}'")
        
        elif is_sponsor_only:
            # Sponsor-only search
            sponsor_term = search_params.get("sponsor_term", "")
            params["query.spons"] = sponsor_term
            st.info(f"Searching for trials with sponsor: {sponsor_term}")
        
        else:
            # Default to disease/condition search
            disease_term = search_params.get("disease_term", "")
            params["query.cond"] = disease_term
            st.info(f"Searching for trials related to: {disease_term}")
        
        # Add filter by status if specified
        if "status_filter" in search_params and search_params["status_filter"]:
            params["filter.overallStatus"] = search_params["status_filter"]
        
        # Add year filter if specified
        if "year_filter" in search_params and search_params["year_filter"]:
            year = search_params["year_filter"]
            # If a specific year is provided, filter by start date
            params["filter.advanced"] = f"AREA[StartDate]{year}"

        # Add sort parameter if specified
        if "sort_by" in search_params and search_params["sort_by"]:
            sort_field = search_params["sort_by"]
            sort_direction = search_params.get("sort_direction", "desc")
            params["sort"] = f"{sort_field}:{sort_direction}"
            
        # Add page token if we're not on the first page
        if "page_token" in search_params and search_params["page_token"]:
            params["pageToken"] = search_params["page_token"]
            
        search_description = "dual filtered studies" if is_dual_search else f"studies for '{search_params.get('disease_term') or search_params.get('sponsor_term')}'"
        
        with st.spinner(f"Fetching {search_description} with advanced filters..."):
            # Make the request
            response = requests.get(API_V2_URL, params=params)
            
            if response.status_code == 200:
                return {"json_content": response.json()}
            else:
                st.error(f"API V2 request failed with status code: {response.status_code}")
                
                # Display more detailed error info
                try:
                    error_content = response.text[:500] + "..." if len(response.text) > 500 else response.text
                    st.error(f"Error response content: {error_content}")
                except:
                    st.error("Could not extract error content from response")
                
                return None
    except Exception as e:
        st.error(f"Error fetching clinical trials from V2 API: {str(e)}")
        return None

def parse_json_response(json_content: Dict) -> List[Dict]:
    """
    Parse JSON response from ClinicalTrials.gov V2 API.
    
    Args:
        json_content: JSON response from the API
        
    Returns:
        List of dictionaries containing extracted trial data
    """
    try:
        studies = []
        
        # Extract study data from each study in the response
        for study in json_content.get("studies", []):
            try:
                study_data = {
                    'nct_id': 'N/A',
                    'brief_title': 'N/A',
                    'phase': 'N/A',
                    'enrollment': 'N/A',
                    'conditions': 'N/A',
                    'interventions': 'N/A',
                    'sponsor': 'N/A',
                    'primary_outcome': 'N/A',
                    'brief_summary': 'N/A',
                    'status': 'N/A',
                    'start_date': None,
                    'primary_completion_date': None,
                    'completion_date': None,
                    'last_update_date': None,
                    'status_verified_date': None
                }
                
                # V2 API Response Structure
                protocol_section = study.get("protocolSection", {})
                
                # Extract identification info
                identification_module = protocol_section.get("identificationModule", {})
                study_data['nct_id'] = identification_module.get("nctId", "N/A")
                study_data['brief_title'] = identification_module.get("briefTitle", "N/A")
                
                # Extract brief summary
                description_module = protocol_section.get("descriptionModule", {})
                study_data['brief_summary'] = description_module.get("briefSummary", "N/A")
                
                # Extract phase
                design_module = protocol_section.get("designModule", {})
                phases = design_module.get("phases", [])
                if phases:
                    study_data['phase'] = ", ".join(phases)
                
                # Extract enrollment
                enrollment_info = design_module.get("enrollmentInfo", {})
                study_data['enrollment'] = str(enrollment_info.get("count", "N/A"))
                
                # Extract conditions
                conditions_module = protocol_section.get("conditionsModule", {})
                conditions = conditions_module.get("conditions", [])
                if conditions:
                    study_data['conditions'] = ", ".join(conditions)
                
                # Extract interventions
                interventions_module = protocol_section.get("armsInterventionsModule", {})
                interventions = interventions_module.get("interventions", [])
                intervention_list = []
                for intervention in interventions:
                    int_type = intervention.get("type", "")
                    int_name = intervention.get("name", "")
                    if int_name:
                        if int_type:
                            intervention_list.append(f"{int_type}: {int_name}")
                        else:
                            intervention_list.append(int_name)
                
                if intervention_list:
                    study_data['interventions'] = ", ".join(intervention_list)
                
                # Extract sponsor
                sponsor_module = protocol_section.get("sponsorCollaboratorsModule", {})
                lead_sponsor = sponsor_module.get("leadSponsor", {})
                study_data['sponsor'] = lead_sponsor.get("name", "N/A")
                
                # Extract primary outcome
                outcomes_module = protocol_section.get("outcomesModule", {})
                primary_outcomes = outcomes_module.get("primaryOutcomes", [])
                if primary_outcomes:
                    primary_outcome = primary_outcomes[0]
                    study_data['primary_outcome'] = primary_outcome.get("measure", "N/A")
                
                # Extract status
                status_module = protocol_section.get("statusModule", {})
                study_data['status'] = status_module.get("overallStatus", "N/A")
                study_data['status_verified_date'] = status_module.get("statusVerifiedDate", None)
                
                # Extract dates
                study_data['start_date'] = status_module.get("startDate", None)
                study_data['primary_completion_date'] = status_module.get("primaryCompletionDate", None)
                study_data['completion_date'] = status_module.get("completionDate", None)
                study_data['last_update_date'] = status_module.get("lastUpdateSubmitDate", None)
                
                # Create a concise summary string for this study
                study_data['concise_summary'] = create_concise_summary(study_data)
                
                # Add to list of studies
                studies.append(study_data)
                
            except Exception as e:
                st.warning(f"Error parsing individual study: {str(e)}")
                continue
                
        return studies
        
    except Exception as e:
        st.error(f"Error parsing JSON response: {str(e)}")
        return []

def create_concise_summary(study_data: Dict) -> str:
    """
    Create a concise, one-line summary of a study for batch LLM analysis.
    
    Args:
        study_data: Dictionary containing extracted study data
        
    Returns:
        A single-line string summary of the study
    """
    # Extract main intervention (first one if multiple)
    main_intervention = study_data['interventions']
    if main_intervention != 'N/A' and ';' in main_intervention:
        main_intervention = main_intervention.split(';')[0].strip()
    
    # Format enrollment count
    enrollment = study_data['enrollment']
    if enrollment != 'N/A':
        enrollment = f"{enrollment} participants"
    
    # Include status and date information
    status = f"Status: {study_data['status']}" if study_data['status'] != 'N/A' else ""
    start_date = f"Started: {study_data['start_date']}" if study_data['start_date'] else ""
    
    # Create the summary string
    summary = f"NCT ID: {study_data['nct_id']}, Title: {study_data['brief_title']}, "
    summary += f"Phase: {study_data['phase']}, Enrollment: {enrollment}, "
    summary += f"Main Intervention: {main_intervention}, Primary Outcome: {study_data['primary_outcome']}, "
    summary += f"Sponsor: {study_data['sponsor']}, Condition: {study_data['conditions']}"
    
    # Add status and date if available
    if status:
        summary += f", {status}"
    if start_date:
        summary += f", {start_date}"
    
    return summary

def analyze_studies_with_llm(studies: List[Dict]) -> Dict:
    """
    Analyze a batch of studies with a single LLM call to identify trends and insights.
    
    Args:
        studies: List of dictionaries containing study data
        
    Returns:
        Dictionary with analysis results
    """
    if not studies:
        return {
            "error": "No studies to analyze",
            "insights": "No insights available"
        }
    
    # Concatenate all study summaries
    summaries = [study['concise_summary'] for study in studies]
    all_summaries_text = "\n".join(summaries)
    
    # Check if we have enough data to send to the LLM
    if len(summaries) < 2:
        return {
            "error": "Insufficient data for analysis",
            "insights": "Not enough studies to provide meaningful analysis. At least 2 studies are required."
        }
    
    prompt = f"""
    Given the following summaries of {len(summaries)} clinical trial studies, analyze and summarize key trends, findings, 
    or interesting insights across all studies. Provide an overall summary, note any notable outliers, frequent sponsors, 
    most common phases or interventions, and any other patterns you find.
    
    Present your answer as a human-readable summary.
    
    Clinical Trial Summaries:
    {all_summaries_text}
    """
    
    # Try up to 3 times with exponential backoff
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            
            analysis = {
                "insights": response.text,
                "studies_analyzed": len(summaries),
                "time_generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return analysis
            
        except Exception as e:
            if attempt < 2:  # If not the last attempt
                wait_time = (2 ** attempt) * 2  # Exponential backoff
                time.sleep(wait_time)
            else:
                return {
                    "error": f"API error: {str(e)}",
                    "insights": "Failed to generate insights. Please try again with fewer studies."
                }

def process_clinical_trials(search_params: Dict) -> Dict:
    """
    Process clinical trials data by fetching from API and parsing response
    with support for advanced filtering and dual queries.
    
    Args:
        search_params: Dictionary containing search parameters and filters
        
    Returns:
        Dictionary containing processed results and analysis
    """
    # Extract basic search parameters
    disease_term = search_params.get("disease_term")
    sponsor_term = search_params.get("sponsor_term")
    is_dual_search = search_params.get("is_dual_search", False)
    is_sponsor_only = search_params.get("is_sponsor_only", False)
    num_studies = search_params.get("num_studies", DEFAULT_NUM_STUDIES)
    
    # For display and reporting purposes
    search_description = []
    if disease_term:
        search_description.append(f"disease: '{disease_term}'")
    if sponsor_term:
        search_description.append(f"sponsor: '{sponsor_term}'")
    search_display = " AND ".join(search_description)
    
    # Warn if trying to retrieve more than the API allows
    if num_studies > MAX_RETRIEVABLE_STUDIES:
        st.warning(f"The API only allows retrieving the first {MAX_RETRIEVABLE_STUDIES} studies. Limiting to this number.")
        num_studies = MAX_RETRIEVABLE_STUDIES
    
    all_studies = []
    
    # Process in batches using V2 API
    total_batches = (num_studies + MAX_RESULTS_PER_PAGE - 1) // MAX_RESULTS_PER_PAGE
    progress_bar = st.progress(0)
    status_text = st.empty()
    processed_count = 0
    next_page_token = None
    
    # Process in batches to respect API limits
    for batch in range(total_batches):
        min_rank = batch * MAX_RESULTS_PER_PAGE + 1
        max_rank = min(min_rank + MAX_RESULTS_PER_PAGE - 1, num_studies)
        
        status_text.text(f"Fetching batch {batch+1}/{total_batches} (studies {min_rank}-{max_rank})...")
        
        # Prepare request params for this batch
        batch_params = search_params.copy()
        batch_params["min_rank"] = min_rank
        batch_params["max_rank"] = max_rank
        
        # Use page token for pagination if we have one
        if next_page_token:
            batch_params["page_token"] = next_page_token
        
        # Fetch data from API
        api_response = fetch_clinical_trials(batch_params)
        
        if not api_response:
            st.warning(f"Failed to fetch batch {batch+1}. Continuing with next batch...")
            continue
        
        # Parse response
        if "json_content" in api_response:
            # Parse JSON response for V2 API
            json_content = api_response["json_content"]
            studies = parse_json_response(json_content)
            
            # Get next page token for pagination
            next_page_token = json_content.get("nextPageToken")
            
            # Get total count if available
            if "totalCount" in json_content and batch == 0:
                total_count = json_content["totalCount"]
                st.info(f"Total studies matching criteria: {total_count}")
        else:
            studies = []
        
        # Add studies to our collection
        all_studies.extend(studies)
        processed_count += len(studies)
        progress_bar.progress(min(processed_count / num_studies, 1.0))
        
        # If we've processed enough studies, break
        if processed_count >= num_studies:
            break
            
        # If there's no next page token, we're done
        if not next_page_token:
            break
            
        # If there are more batches but we didn't get any studies in this one, break
        if len(studies) == 0 and batch < total_batches - 1:
            st.warning("No more studies found. Stopping retrieval.")
            break
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Enrich studies with financial data
    with st.spinner("Enriching studies with financial data..."):
        enriched_studies = fin.enrich_studies_with_financial_data(all_studies)
    
    # Only analyze if we have studies
    if enriched_studies:
        with st.spinner("Analyzing studies to identify trends and insights..."):
            analysis_results = analyze_studies_with_llm(enriched_studies)
    else:
        analysis_results = {
            "error": "No studies to analyze",
            "insights": "No insights available"
        }
    
    return {
        "studies": enriched_studies,
        "analysis": analysis_results,
        "search_description": search_display,
        "studies_found": len(enriched_studies),
        "filters_applied": {
            "disease": disease_term,
            "sponsor": sponsor_term,
            "year": search_params.get("year_filter"),
            "status": search_params.get("status_filter")
        }
    }

def display_detailed_results(results_df):
    """Display detailed results for each study in expandable sections."""
    st.subheader("Detailed Results")
    
    for i, row in results_df.iterrows():
        with st.expander(f"{row['nct_id']}: {row['brief_title']}"):
            # Remove fields not needed for display
            display_fields = ['nct_id', 'brief_title', 'phase', 'enrollment', 
                             'conditions', 'interventions', 'sponsor', 
                             'primary_outcome', 'status']
            display_row = {k: v for k, v in row.items() if k in display_fields}
            
            # Create tabs for different types of information
            tab1, tab2, tab3 = st.tabs(["Trial Information", "Market Analysis", "Forecasting"])
            
            # Tab 1: Trial Information
            with tab1:
                # Display as two columns
                cols = st.columns(2)
                for j, (key, value) in enumerate(display_row.items()):
                    col_idx = j % 2
                    with cols[col_idx]:
                        st.markdown(f"**{key.replace('_', ' ').title()}**: {value}")
                
                # Display dates if available in a new row
                st.markdown("---")
                st.markdown("**Timeline Information**")
                date_cols = st.columns(4)
                
                with date_cols[0]:
                    start_date = row.get('start_date')
                    if start_date:
                        st.markdown(f"**Start Date**: {start_date}")
                
                with date_cols[1]:
                    primary_completion = row.get('primary_completion_date')
                    if primary_completion:
                        st.markdown(f"**Primary Completion**: {primary_completion}")
                
                with date_cols[2]:
                    completion = row.get('completion_date')
                    if completion:
                        st.markdown(f"**Completion Date**: {completion}")
                
                with date_cols[3]:
                    last_update = row.get('last_update_date')
                    if last_update:
                        st.markdown(f"**Last Update**: {last_update}")
                
                # Display brief summary if available
                if row['brief_summary'] != 'N/A':
                    st.markdown("---")
                    st.markdown("**Brief Summary**")
                    st.markdown(row['brief_summary'])
            
            # Tab 2: Market Analysis (if financial data is available)
            with tab2:
                if 'has_financial_data' in row and row['has_financial_data']:
                    # Display stock ticker and company
                    st.markdown(f"**Company**: {row['sponsor']} ({row['ticker']})")
                    
                    # Display market metrics
                    if 'market_metrics' in row:
                        metrics = row['market_metrics']
                        cols = st.columns(4)
                        
                        with cols[0]:
                            st.metric("Price Change (%)", 
                                     f"{metrics['price_change_pct']:.2f}%" if metrics['price_change_pct'] is not None else "N/A")
                        
                        with cols[1]:
                            st.metric("Avg Daily Return", 
                                     f"{metrics['avg_daily_return']:.2f}%" if metrics['avg_daily_return'] is not None else "N/A")
                        
                        with cols[2]:
                            st.metric("Volatility", 
                                     f"{metrics['volatility']:.2f}%" if metrics['volatility'] is not None else "N/A")
                        
                        with cols[3]:
                            st.metric("Volume Change", 
                                     f"{metrics['volume_change_pct']:.2f}%" if metrics['volume_change_pct'] is not None else "N/A")
                    
                    # Show stock chart
                    if st.button(f"Show {row['ticker']} Stock Chart", key=f"chart_{i}"):
                        with st.spinner(f"Fetching stock data for {row['ticker']}..."):
                            # Fetch stock data
                            stock_data = fin.fetch_stock_data(row['ticker'])
                            
                            if stock_data is not None:
                                # Create and display chart
                                fig = fin.plot_stock_data(stock_data, row['ticker'])
                                st.pyplot(fig)
                            else:
                                st.warning(f"No stock data available for {row['ticker']}")
                    
                    # Generate market impact analysis
                    if st.button(f"Analyze Market Impact", key=f"impact_{i}"):
                        with st.spinner(f"Analyzing market impact for {row['ticker']}..."):
                            # Fetch stock data
                            stock_data = fin.fetch_stock_data(row['ticker'])
                            
                            if stock_data is not None:
                                # Generate analysis
                                analysis = fin.analyze_market_impact(row, stock_data, row['ticker'])
                                st.markdown("### Market Impact Analysis")
                                st.markdown(analysis)
                            else:
                                st.warning(f"No stock data available for {row['ticker']}")
                else:
                    st.markdown("No financial data available for this clinical trial's sponsor.")
                    
                    if 'sponsor' in row and row['sponsor'] != 'N/A':
                        st.markdown(f"Sponsor: {row['sponsor']}")
                        st.markdown("This sponsor was not matched to a publicly traded company in our database.")
                    else:
                        st.markdown("No sponsor information available for this trial.")
                        
            # Tab 3: Forecasting (if financial data is available)
            with tab3:
                if 'has_financial_data' in row and row['has_financial_data']:
                    st.markdown("### Stock Price Forecasting with ARIMA")
                    st.markdown("This tab provides stock price forecasting based on an ARIMA model, with clinical trial events marked on the timeline.")
                    
                    if st.button(f"Generate {row['ticker']} Forecast", key=f"forecast_{i}"):
                        with st.spinner(f"Building ARIMA model for {row['ticker']}..."):
                            # Fetch more stock data for better modeling
                            stock_data = fin.fetch_stock_data(row['ticker'], days=365)  # Get a year of data
                            
                            if stock_data is not None and not stock_data.empty:
                                # Extract trial dates
                                trial_dates = [
                                    row.get('start_date'),
                                    row.get('primary_completion_date'),
                                    row.get('completion_date'),
                                    row.get('last_update_date')
                                ]
                                trial_dates = [d for d in trial_dates if d is not None]
                                
                                # Build ARIMA model
                                model_results = fin.build_arima_model(stock_data, trial_dates)
                                
                                if model_results:
                                    # Display model metrics
                                    st.write("### ARIMA Model Statistics")
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("Model Parameters", f"p={model_results['p']}, d={model_results['d']}, q={model_results['q']}")
                                    with col2:
                                        st.metric("Data Stationarity", "Yes" if model_results['is_stationary'] else "No")
                                    with col3:
                                        st.metric("Days Forecasted", "30")
                                    
                                    # Create and show forecast plot
                                    fig = fin.plot_stock_forecast(row['ticker'], stock_data, model_results, row)
                                    st.pyplot(fig)
                                    
                                    # Display forecast values
                                    st.write("### 30-Day Price Forecast")
                                    forecast_df = model_results['forecast'].reset_index()
                                    forecast_df.columns = ['Day', 'Forecast', 'Lower CI', 'Upper CI']
                                    forecast_df['Day'] = forecast_df.index + 1
                                    forecast_df = forecast_df[['Day', 'Forecast', 'Lower CI', 'Upper CI']]
                                    forecast_df = forecast_df.round(2)
                                    st.dataframe(forecast_df)
                                    
                                    # Generate LLM commentary
                                    forecast_analysis = fin.analyze_forecast_impact(row, stock_data, model_results, row['ticker'])
                                    st.write("### AI Analysis of Forecast")
                                    st.write(forecast_analysis)
                                else:
                                    st.warning("Failed to build ARIMA forecast model. Check if the stock data is suitable for modeling.")
                            else:
                                st.warning(f"No stock data available for {row['ticker']}. Please try an alternative ticker if known.")
                else:
                    st.markdown("No financial data available for this clinical trial's sponsor.")
                    st.markdown("Forecasting requires financial data from a publicly traded company.")
                    st.markdown("This trial's sponsor could not be matched to a stock ticker in our database.")

def display_search_page():
    """Display the search page for querying clinical trials."""
    st.subheader("Search and Filter Options")
    
    # Main search parameters
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Replace generic search term with specific disease/condition field
        disease_term = st.text_input("Disease/Condition", "diabetes", 
                                     help="Enter a disease or condition to search for")
    
    with col2:
        num_studies = st.number_input("Number of Studies", 
                                      min_value=1, 
                                      max_value=MAX_ALLOWED_STUDIES, 
                                      value=DEFAULT_NUM_STUDIES)
    
    # Add sponsor field for dual filtering
    sponsor_term = st.text_input("Sponsor Company (Optional)", 
                                placeholder="e.g., Pfizer, Novartis", 
                                help="Enter a sponsor company name to filter by")
    
    # Advanced filtering options
    with st.expander("Advanced Filtering Options", expanded=True):
        filter_cols = st.columns(3)
        
        # Remove the search type radio button since we now have dedicated fields
        
        with filter_cols[0]:
            # Year filter dropdown
            current_year = datetime.datetime.now().year
            year_options = ["Any Year"] + [str(year) for year in range(current_year, current_year-20, -1)]
            year_filter = st.selectbox(
                "Filter by Year (Start Date)",
                options=year_options,
                index=0,
                help="Filter studies by their start year"
            )
            # Convert "Any Year" to None for API parameter
            year_filter = None if year_filter == "Any Year" else year_filter
        
        with filter_cols[1]:
            # Status filter
            status_options = [
                "Any Status",
                "RECRUITING",
                "ACTIVE_NOT_RECRUITING",
                "COMPLETED",
                "NOT_YET_RECRUITING",
                "ENROLLING_BY_INVITATION",
                "SUSPENDED",
                "TERMINATED",
                "WITHDRAWN"
            ]
            status_filter = st.selectbox(
                "Filter by Status",
                options=status_options,
                index=0,
                help="Filter studies by their current status"
            )
            # Convert "Any Status" to None for API parameter
            status_filter = None if status_filter == "Any Status" else status_filter
            
        with filter_cols[2]:
            # Add a placeholder to balance the columns
            st.write("&nbsp;")
        
        # Sorting options
        sort_cols = st.columns(2)
        
        with sort_cols[0]:
            sort_options = [
                ("Relevance", "@relevance"),
                ("Last Update Date", "LastUpdatePostDate"),
                ("Start Date", "StartDate"),
                ("Completion Date", "CompletionDate"),
                ("Enrollment Count", "EnrollmentCount")
            ]
            sort_by = st.selectbox(
                "Sort Results By",
                options=[option[0] for option in sort_options],
                index=0,
                help="Choose how to sort the results"
            )
            # Map display name to API parameter
            sort_by_param = next((option[1] for option in sort_options if option[0] == sort_by), "@relevance")
        
        with sort_cols[1]:
            sort_direction = st.radio(
                "Sort Direction",
                options=["Descending", "Ascending"],
                index=0,
                horizontal=True
            )
            # Convert to API parameter
            sort_direction_param = "desc" if sort_direction == "Descending" else "asc"
    
    # Search button
    if st.button("Search and Analyze"):
        if not disease_term and not sponsor_term:
            st.error("Please enter at least a disease/condition or sponsor term.")
        else:
            # Determine search mode based on input
            is_dual_search = disease_term and sponsor_term
            is_sponsor_only = not disease_term and sponsor_term
            
            # Prepare search parameters
            search_params = {
                "disease_term": disease_term if disease_term else None,
                "sponsor_term": sponsor_term if sponsor_term else None,
                "is_dual_search": is_dual_search,
                "is_sponsor_only": is_sponsor_only,
                "num_studies": num_studies,
                "year_filter": year_filter,
                "status_filter": status_filter,
                "sort_by": sort_by_param,
                "sort_direction": sort_direction_param
            }
            
            # Display applied filters
            filter_info = []
            if disease_term:
                filter_info.append(f"Disease/Condition: {disease_term}")
            if sponsor_term:
                filter_info.append(f"Sponsor: {sponsor_term}")
            if year_filter:
                filter_info.append(f"Year: {year_filter}")
            if status_filter:
                filter_info.append(f"Status: {status_filter}")
                
            filter_display = " | ".join(filter_info)
            
            st.info(f"""
            Search mode: {"Dual Filter" if is_dual_search else "Sponsor Only" if is_sponsor_only else "Disease/Condition Only"}
            Filters: {filter_display}
            Sorting by: {sort_by} ({sort_direction})
            """)
            
            # Process clinical trials
            results = process_clinical_trials(search_params)
            
            # Store results in session state
            st.session_state.current_results = results["studies"]
            st.session_state.current_results_df = pd.DataFrame(results["studies"])
            st.session_state.last_search_params = search_params
            st.session_state.llm_analysis = results["analysis"]
            
            # Switch to analysis page
            st.session_state.page = "analysis"
            st.rerun()

def display_analysis_page():
    """Display the analysis page for reviewing search results."""
    if st.session_state.current_results_df is None or len(st.session_state.current_results_df) == 0:
        st.warning("No results to display. Please run a search first.")
        return
    
    results_df = st.session_state.current_results_df
    analysis = st.session_state.llm_analysis
    
    # Display AI-generated insights
    st.subheader("AI Analysis and Insights")
    insights_container = st.container()
    with insights_container:
        st.markdown("---")
        if "error" in analysis and analysis["error"] != "":
            st.warning(analysis["error"])
        st.markdown(analysis["insights"])
        st.markdown("---")
        
        # Safely handle the studies_analyzed key which might be missing
        studies_analyzed = analysis.get("studies_analyzed", len(results_df))
        time_generated = analysis.get("time_generated", "Not available")
        
        st.caption(f"Analysis based on {studies_analyzed} studies | Generated: {time_generated}")
    
    # Display a summary of processing results
    st.subheader("Processing Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Studies Found", len(results_df))
    with col2:
        # Get the search description that includes both disease and sponsor
        search_description = st.session_state.last_search_params.get("search_description", "N/A")
        st.metric("Search Criteria", search_description)
    with col3:
        # Count studies with financial data
        financial_studies = sum(1 for study in st.session_state.current_results if study.get('has_financial_data', False))
        st.metric("Studies with Financial Data", financial_studies)
    
    # Display filters applied
    filters_applied = st.session_state.last_search_params.get("filters_applied", {})
    
    if any(filter_value for filter_value in filters_applied.values() if filter_value):
        st.subheader("Filters Applied")
        filter_cols = st.columns(4)
        
        with filter_cols[0]:
            if filters_applied.get("disease"):
                st.info(f"Disease: {filters_applied['disease']}")
        
        with filter_cols[1]:
            if filters_applied.get("sponsor"):
                st.info(f"Sponsor: {filters_applied['sponsor']}")
        
        with filter_cols[2]:
            if filters_applied.get("year"):
                st.info(f"Year: {filters_applied['year']}")
        
        with filter_cols[3]:
            if filters_applied.get("status"):
                st.info(f"Status: {filters_applied['status']}")
    
    # Display results table
    st.subheader("Extracted Information")
    
    # Add financial data columns if present
    display_cols = ['nct_id', 'brief_title', 'phase', 'enrollment', 
                   'conditions', 'interventions', 'sponsor', 
                   'primary_outcome', 'status']
    
    # Add date columns if showing time-related info
    if st.checkbox("Show Timeline Information", value=True):
        date_cols = ['start_date', 'primary_completion_date', 'completion_date', 'last_update_date']
        display_cols.extend([col for col in date_cols if col in results_df.columns])
    
    # Add financial columns if they exist
    if 'ticker' in results_df.columns:
        display_cols.append('ticker')
    
    # Create display dataframe
    display_df = results_df[display_cols]
    
    # Add option to show/hide financial data
    show_financial = st.checkbox("Show Financial Impact", value=True)
    
    if show_financial:
        # Create a filtered view with only financially analyzable trials
        if 'has_financial_data' in results_df.columns:
            financial_df = results_df[results_df['has_financial_data'] == True]
            if not financial_df.empty:
                st.subheader("Financial Impact Overview")
                st.dataframe(financial_df[display_cols], use_container_width=True)
    
    # Show all trials
    st.subheader("All Clinical Trials")
    st.dataframe(display_df, use_container_width=True)
    
    # Display detailed results for each file
    display_detailed_results(results_df)
    
    # Download buttons for CSV
    st.subheader("Download Options")
    
    # Prepare financial metrics for export
    export_df = display_df.copy()
    
    # Add financial metrics if they exist
    if 'has_financial_data' in results_df.columns and 'market_metrics' in results_df.columns:
        # Extract financial metrics into separate columns
        financial_rows = results_df[results_df['has_financial_data'] == True]
        
        # Initialize new columns
        export_df['price_change_pct'] = None
        export_df['avg_daily_return'] = None
        export_df['volatility'] = None
        export_df['volume_change_pct'] = None
        
        # Update values for rows with financial data
        for idx, row in financial_rows.iterrows():
            if 'market_metrics' in row and row['market_metrics'] is not None:
                metrics = row['market_metrics']
                export_df.loc[idx, 'price_change_pct'] = metrics.get('price_change_pct')
                export_df.loc[idx, 'avg_daily_return'] = metrics.get('avg_daily_return')
                export_df.loc[idx, 'volatility'] = metrics.get('volatility')
                export_df.loc[idx, 'volume_change_pct'] = metrics.get('volume_change_pct')
    
    # Download button for CSV
    csv = export_df.to_csv(index=False)
    
    # Create a more descriptive filename including disease and sponsor if available
    file_parts = []
    if filters_applied.get("disease"):
        file_parts.append(filters_applied["disease"].replace(" ", "_"))
    if filters_applied.get("sponsor"):
        file_parts.append(filters_applied["sponsor"].replace(" ", "_"))
    if not file_parts:
        file_parts.append("results")
    
    file_base = "_".join(file_parts)
    
    if filters_applied.get("year"):
        file_base += f"_{filters_applied['year']}"
    
    file_name = f"clinical_trial_analysis_{file_base}_{len(results_df)}.csv"
    
    st.download_button(
        label="Download Results as CSV",
        data=csv,
        file_name=file_name,
        mime="text/csv",
    )
    
    # Also download insights as text file
    insights_text = analysis["insights"]
    st.download_button(
        label="Download AI Analysis as Text",
        data=insights_text,
        file_name=f"clinical_trial_insights_{file_base}_{len(results_df)}.txt",
        mime="text/plain",
    )

def display_saved_studies_page():
    """Display the saved studies page."""
    st.header("Saved Studies")
    
    if not st.session_state.saved_studies:
        st.info("You haven't saved any studies yet. Search for clinical trials and save them to view them here.")
        
        if st.button("Go to Search Page"):
            st.session_state.page = "search"
            st.rerun()
            
        return
    
    st.write(f"You have {len(st.session_state.saved_studies)} saved studies.")
    
    # Display saved studies in a table
    saved_df = pd.DataFrame(st.session_state.saved_studies)
    
    # Basic columns to always show
    display_cols = ['nct_id', 'brief_title', 'phase', 'sponsor', 'status']
    
    # Add ticker if available
    if 'ticker' in saved_df.columns:
        display_cols.append('ticker')
        
    # Show the data
    st.dataframe(saved_df[display_cols], use_container_width=True)
    
    # Button to clear all saved studies
    if st.button("Clear All Saved Studies"):
        st.session_state.saved_studies = []
        st.success("All saved studies have been cleared.")
        st.rerun()
    
    # Detailed view of selected study
    st.subheader("Study Details")
    
    # Create a selection widget for studies
    study_options = {f"{study.get('brief_title', 'Unknown')} ({study.get('nct_id', 'Unknown')})": i 
                   for i, study in enumerate(st.session_state.saved_studies)}
    
    selected_study_title = st.selectbox(
        "Select a study to view details:", 
        list(study_options.keys())
    )
    
    if selected_study_title:
        study_index = study_options[selected_study_title]
        selected_study = st.session_state.saved_studies[study_index]
        
        # Display study details in tabs
        tab1, tab2 = st.tabs(["Study Information", "Financial Impact"])
        
        with tab1:
            # Display study details
            st.markdown(f"**NCT ID:** {selected_study.get('nct_id', 'N/A')}")
            st.markdown(f"**Title:** {selected_study.get('brief_title', 'N/A')}")
            st.markdown(f"**Phase:** {selected_study.get('phase', 'N/A')}")
            st.markdown(f"**Status:** {selected_study.get('status', 'N/A')}")
            st.markdown(f"**Sponsor:** {selected_study.get('sponsor', 'N/A')}")
            st.markdown(f"**Conditions:** {selected_study.get('conditions', 'N/A')}")
            st.markdown(f"**Interventions:** {selected_study.get('interventions', 'N/A')}")
            
            # Display timeline
            st.subheader("Timeline")
            st.markdown(f"**Start Date:** {selected_study.get('start_date', 'N/A')}")
            st.markdown(f"**Primary Completion:** {selected_study.get('primary_completion_date', 'N/A')}")
            st.markdown(f"**Completion Date:** {selected_study.get('completion_date', 'N/A')}")
            
            # Display summary
            if selected_study.get('brief_summary', 'N/A') != 'N/A':
                st.subheader("Brief Summary")
                st.markdown(selected_study.get('brief_summary', 'N/A'))
        
        with tab2:
            if selected_study.get('has_financial_data', False):
                ticker = selected_study.get('ticker', 'N/A')
                st.subheader(f"Financial Impact ({ticker})")
                
                # Display market metrics if available
                if 'market_metrics' in selected_study:
                    metrics = selected_study['market_metrics']
                    cols = st.columns(4)
                    
                    with cols[0]:
                        st.metric("Price Change (%)", 
                                 f"{metrics.get('price_change_pct', 'N/A'):.2f}%" if metrics.get('price_change_pct') is not None else "N/A")
                    
                    with cols[1]:
                        st.metric("Avg Daily Return", 
                                 f"{metrics.get('avg_daily_return', 'N/A'):.2f}%" if metrics.get('avg_daily_return') is not None else "N/A")
                    
                    with cols[2]:
                        st.metric("Volatility", 
                                 f"{metrics.get('volatility', 'N/A'):.2f}%" if metrics.get('volatility') is not None else "N/A")
                    
                    with cols[3]:
                        st.metric("Volume Change", 
                                 f"{metrics.get('volume_change_pct', 'N/A'):.2f}%" if metrics.get('volume_change_pct') is not None else "N/A")
                
                # Stock chart button
                if st.button(f"Show {ticker} Stock Chart"):
                    with st.spinner(f"Fetching stock data for {ticker}..."):
                        # Fetch stock data
                        stock_data = fin.fetch_stock_data(ticker)
                        
                        if stock_data is not None:
                            # Create and display chart
                            fig = fin.plot_stock_data(stock_data, ticker)
                            st.pyplot(fig)
                        else:
                            st.warning(f"No stock data available for {ticker}")
                
                # Trial phase analysis button
                if st.button("Analyze Trial Phase Impact on Stock"):
                    st.session_state.page = "trial_stock"
                    # Set the selected study to analyze
                    st.session_state.selected_study_for_analysis = selected_study
                    st.rerun()
                    
            else:
                st.info("No financial data available for this study's sponsor.")

def display_trial_stock_analysis_page():
    """
    Display the trial-stock correlation analysis page.
    This page focuses on analyzing the relationship between clinical trial phases and stock price movements.
    """
    st.header("Clinical Trial & Stock Price Correlation Analysis")
    st.markdown("""
    This page analyzes how clinical trial events and phases correlate with stock price movements for pharmaceutical and biotech companies.
    """)
    
    # Check if we have studies with financial data
    studies_with_financial_data = []
    
    if st.session_state.current_results is not None:
        studies_with_financial_data = [
            study for study in st.session_state.current_results 
            if study.get('has_financial_data', False) and study.get('ticker') is not None
        ]
    
    if not studies_with_financial_data:
        st.warning("No studies with financial data available. Please run a search for clinical trials with matching stock tickers.")
        
        # Add a button to go to search page
        if st.button("Go to Search Page"):
            st.session_state.page = "search"
            st.rerun()
    
    else:
        # Show number of studies with financial data
        st.success(f"Found {len(studies_with_financial_data)} studies with financial data")
        
        # Select study to analyze
        study_titles = {f"{study.get('brief_title', 'Unknown')} ({study.get('ticker', 'Unknown')})": i 
                       for i, study in enumerate(studies_with_financial_data)}
        
        selected_study_title = st.selectbox(
            "Select a study to analyze the correlation with stock price:", 
            list(study_titles.keys())
        )
        
        if selected_study_title:
            study_index = study_titles[selected_study_title]
            selected_study = studies_with_financial_data[study_index]
            
            # Display study details in columns
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Study Details")
                st.markdown(f"**Title:** {selected_study.get('brief_title', 'N/A')}")
                st.markdown(f"**NCT ID:** {selected_study.get('nct_id', 'N/A')}")
                st.markdown(f"**Phase:** {selected_study.get('phase', 'N/A')}")
                st.markdown(f"**Status:** {selected_study.get('overall_status', 'N/A')}")
                
                # Handle conditions which might be a string or a list
                conditions = selected_study.get('condition', ['N/A'])
                if isinstance(conditions, list):
                    conditions_str = ', '.join(conditions)
                else:
                    conditions_str = conditions
                
                st.markdown(f"**Conditions:** {conditions_str}")
                st.markdown(f"**Sponsor:** {selected_study.get('sponsor', 'N/A')}")
            
            with col2:
                st.subheader("Timeline")
                st.markdown(f"**Start Date:** {selected_study.get('start_date', 'N/A')}")
                st.markdown(f"**Primary Completion:** {selected_study.get('primary_completion_date', 'N/A')}")
                st.markdown(f"**Completion Date:** {selected_study.get('completion_date', 'N/A')}")
                st.markdown(f"**Last Update:** {selected_study.get('last_update_date', 'N/A')}")
                st.markdown(f"**Results Posted:** {selected_study.get('results_first_posted_date', 'N/A')}")
                
                # Display market metrics if available
                if 'market_metrics' in selected_study:
                    st.subheader("Market Metrics")
                    metrics = selected_study['market_metrics']
                    price_change = metrics.get('price_change_pct')
                    if price_change is not None:
                        color = "positive" if price_change > 0 else "negative" if price_change < 0 else ""
                        st.markdown(f"**Price Change:** <span class='{color}'>{price_change:.2f}%</span>", unsafe_allow_html=True)
                    
                    st.markdown(f"**Avg. Daily Return:** {metrics.get('avg_daily_return', 'N/A'):.2f}%")
                    st.markdown(f"**Volatility:** {metrics.get('volatility', 'N/A'):.2f}%")
            
            # Get ticker and display trial phase impact analysis
            ticker = selected_study.get('ticker')
            
            if ticker and ticker != 'N/A':
                st.subheader(f"{ticker} Stock Price Analysis with Trial Events")
                
                # Fetch stock data for a longer period
                days_to_fetch = 365  # Default to 1 year of data
                
                # Get trial start date if available
                start_date_str = selected_study.get('start_date')
                if start_date_str:
                    try:
                        # Try to parse the start date
                        for fmt in ['%Y-%m-%d', '%B %Y', '%b %d, %Y']:
                            try:
                                start_date = datetime.datetime.strptime(start_date_str, fmt)
                                # Calculate days from start date to now
                                days_since_start = (datetime.datetime.now() - start_date).days
                                # Add some buffer before the start date
                                days_to_fetch = max(days_since_start + 30, 365)
                                break
                            except:
                                continue
                    except Exception as e:
                        st.warning(f"Could not parse start date: {start_date_str}, error: {e}")
                
                # Check cache first before fetching stock data
                cache_key = f"{ticker}_{days_to_fetch}"
                stock_data = None
                
                if hasattr(st.session_state, 'stock_data_cache') and cache_key in st.session_state.stock_data_cache:
                    cache_entry = st.session_state.stock_data_cache[cache_key]
                    cache_time = cache_entry.get('timestamp')
                    
                    # Cache is valid for 1 hour
                    if cache_time and (datetime.datetime.now() - cache_time).seconds < 3600:
                        stock_data = cache_entry.get('data')
                        st.success(f"Using cached stock data for {ticker}")
                
                # Fetch if not in cache
                if stock_data is None:
                    with st.spinner(f"Fetching extended stock data for {ticker}..."):
                        stock_data = fin.fetch_stock_data(ticker, days=days_to_fetch)
                
                if stock_data is not None:
                    # Create and display the trial phase stock analysis visualization
                    try:
                        fig = fin.plot_trial_phase_stock_analysis(stock_data, selected_study, ticker)
                        if fig:
                            st.pyplot(fig)
                    except Exception as e:
                        st.error(f"Error creating visualization: {e}")
                    
                    # Check if impact analysis exists, if not calculate it
                    if 'trial_impact_analysis' not in selected_study:
                        with st.spinner("Calculating trial phase impact on stock..."):
                            impact_analysis = fin.analyze_trial_phase_impact(stock_data, selected_study, ticker)
                            selected_study['trial_impact_analysis'] = impact_analysis
                            
                            # Update in the main results list
                            for i, study in enumerate(st.session_state.current_results):
                                if study.get('nct_id') == selected_study.get('nct_id'):
                                    st.session_state.current_results[i]['trial_impact_analysis'] = impact_analysis
                                    break
                    else:
                        impact_analysis = selected_study['trial_impact_analysis']
                    
                    # Display trial impact analysis if available
                    if impact_analysis and 'error' not in impact_analysis:
                        st.subheader("Trial Phase Impact Analysis")
                        
                        # Extract sentiment
                        sentiment = impact_analysis.get('market_sentiment', 'Neutral')
                        sentiment_color = "positive" if sentiment in ["Positive", "Very Positive"] else "negative" if sentiment in ["Negative", "Very Negative"] else ""
                        
                        st.markdown(f"**Market Sentiment:** <span class='{sentiment_color}'>{sentiment}</span>", unsafe_allow_html=True)
                        
                        # Show event impacts in expandable sections
                        st.markdown("### Event Impact Details")
                        
                        for event_name, event_data in impact_analysis.items():
                            if isinstance(event_data, dict) and 'windows' in event_data:
                                # Create expandable section for each event
                                with st.expander(f"{event_name} ({event_data.get('date', 'N/A')})"):
                                    # Create a table for the window metrics
                                    metrics_data = []
                                    for window_name, window_metrics in event_data['windows'].items():
                                        # Format window name
                                        window_parts = window_name.split('_')
                                        window_display = f"{window_parts[0]} before, {window_parts[2]} after"
                                        
                                        metrics_data.append({
                                            "Window": window_display,
                                            "Window Change": f"{window_metrics['window_price_change_pct']:.2f}%",
                                            "Pre-Event Change": f"{window_metrics['pre_event_change_pct']:.2f}%",
                                            "Post-Event Change": f"{window_metrics['post_event_change_pct']:.2f}%",
                                            "Volume Change": f"{window_metrics['volume_change_pct']:.2f}%"
                                        })
                                    
                                    # Convert to DataFrame and display
                                    metrics_df = pd.DataFrame(metrics_data)
                                    st.table(metrics_df)
                    
                    # Display trial-stock correlation analysis from LLM
                    if 'trial_stock_correlation' in selected_study:
                        st.subheader("Comprehensive Trial-Stock Correlation Analysis")
                        correlation_analysis = selected_study.get('trial_stock_correlation', "Analysis not available")
                        st.markdown(correlation_analysis)
                    else:
                        # If the analysis doesn't exist yet, provide option to generate it
                        if st.button("Generate Trial-Stock Correlation Analysis"):
                            with st.spinner("Analyzing trial and stock correlation..."):
                                # Calculate impact analysis if not already done
                                if 'trial_impact_analysis' not in selected_study:
                                    impact_analysis = fin.analyze_trial_phase_impact(stock_data, selected_study, ticker)
                                    selected_study['trial_impact_analysis'] = impact_analysis
                                else:
                                    impact_analysis = selected_study['trial_impact_analysis']
                                
                                # Generate correlation analysis
                                correlation_analysis = fin.generate_trial_stock_correlation_analysis(
                                    selected_study, stock_data, impact_analysis, ticker)
                                
                                # Update the study with the new analysis
                                selected_study['trial_stock_correlation'] = correlation_analysis
                                
                                # Update in the main results list
                                for i, study in enumerate(st.session_state.current_results):
                                    if study.get('nct_id') == selected_study.get('nct_id'):
                                        st.session_state.current_results[i]['trial_stock_correlation'] = correlation_analysis
                                        break
                                
                                # Show the analysis
                                st.subheader("Comprehensive Trial-Stock Correlation Analysis")
                                st.markdown(correlation_analysis)
                
                else:
                    st.error(f"No stock data available for {ticker}")
            
            else:
                st.error("No ticker symbol associated with this study")

def display_trial_event_impact_page():
    """
    Display the trial event impact page for analyzing the impact of trial events
    on stock prices with a comparative before/after approach.
    """
    st.header("Clinical Trial Event Impact Analysis")
    
    st.write("""
    This tool analyzes the impact of specific clinical trial events on stock prices
    by comparing the price, volume, and volatility metrics before and after the event.
    """)
    
    # Create layout for input parameters
    col1, col2 = st.columns(2)
    
    with col1:
        ticker = st.text_input("Stock Ticker", "AAPL", help="Enter the stock ticker symbol")
        
    with col2:
        date_str = st.date_input("Event Date", 
                                 value=datetime.datetime.now().date() - datetime.timedelta(days=30),
                                 help="Select the date of the clinical trial event")
        
    # Additional parameters in an expander
    with st.expander("Analysis Parameters", expanded=False):
        window_days = st.slider("Analysis Window (days before/after)", 
                               min_value=5, max_value=60, value=15,
                               help="Number of days to analyze before and after the event")
        
        event_name = st.text_input("Event Name", "Trial Milestone", 
                                  help="Name of the event for labeling in the analysis")
    
    # Execute button
    if st.button("Analyze Event Impact"):
        if ticker and date_str:
            try:
                with st.spinner(f"Analyzing impact of {event_name} on {ticker} around {date_str}..."):
                    # Fetch stock data with sufficient buffer
                    days_needed = window_days * 3  # Buffer for weekends and holidays
                    stock_data = fin.fetch_stock_data(ticker, days=days_needed)
                    
                    if stock_data is None or stock_data.empty:
                        st.error(f"Could not fetch stock data for {ticker}")
                    else:
                        # Convert date to datetime
                        event_date = datetime.datetime.combine(date_str, datetime.time.min)
                        
                        # Calculate daily returns if not present
                        if 'Daily Return' not in stock_data.columns:
                            stock_data['Daily Return'] = stock_data['Close'].pct_change() * 100
                        
                        # Run the event impact analysis
                        impact_result = fin.analyze_trial_event_impact(
                            stock_data, 
                            event_date, 
                            window_days_before=window_days, 
                            window_days_after=window_days,
                            event_name=event_name
                        )
                        
                        if "error" in impact_result:
                            st.error(f"Analysis error: {impact_result['error']}")
                        else:
                            # Display success message
                            st.success(f"Successfully analyzed the impact of {event_name} on {ticker}")
                            
                            # Create visualization
                            fig = fin.plot_event_impact(impact_result, ticker)
                            st.pyplot(fig)
                            
                            # Display detailed metrics in tabs
                            price_tab, volume_tab, stats_tab = st.tabs(["Price Analysis", "Volume Analysis", "Statistical Analysis"])
                            
                            with price_tab:
                                st.subheader("Price Change Analysis")
                                
                                # Create metrics display
                                metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                                
                                with metrics_col1:
                                    pre_change = impact_result['price_metrics']['pre_window_change_pct']
                                    st.metric("Pre-Event Change", 
                                             f"{pre_change:.2f}%")
                                    
                                with metrics_col2:
                                    post_change = impact_result['price_metrics']['post_window_change_pct']
                                    st.metric("Post-Event Change", 
                                             f"{post_change:.2f}%",
                                             delta=f"{post_change - pre_change:.2f}%")
                                    
                                with metrics_col3:
                                    event_change = impact_result['price_metrics']['event_day_change_pct']
                                    st.metric("Event Day Change", 
                                             f"{event_change:.2f}%")
                                
                                # Create detailed price metrics table
                                price_data = []
                                for key, value in impact_result['price_metrics'].items():
                                    if isinstance(value, (int, float)):
                                        if 'price' in key:
                                            # Format as dollar amount
                                            formatted_value = f"${value:.2f}"
                                        elif 'pct' in key or 'change' in key:
                                            # Format as percentage
                                            formatted_value = f"{value:.2f}%"
                                        else:
                                            formatted_value = f"{value:.4f}"
                                            
                                        price_data.append({
                                            "Metric": key.replace('_', ' ').title(),
                                            "Value": formatted_value
                                        })
                                
                                st.table(pd.DataFrame(price_data))
                            
                            with volume_tab:
                                st.subheader("Volume Analysis")
                                
                                # Create volume metrics display
                                vol_col1, vol_col2 = st.columns(2)
                                
                                with vol_col1:
                                    vol_change = impact_result['volume_metrics']['volume_change_pct']
                                    st.metric("Average Volume Change", 
                                             f"{vol_change:.2f}%")
                                    
                                with vol_col2:
                                    max_vol_change = impact_result['volume_metrics']['max_volume_change_pct']
                                    st.metric("Maximum Volume Change", 
                                             f"{max_vol_change:.2f}%")
                                
                                # Plot volume data
                                vol_fig, ax = plt.subplots(figsize=(10, 6))
                                
                                # Calculate date for event
                                event_date = impact_result['event_date']
                                
                                # Plot pre-event volume
                                pre_data = impact_result['pre_event_data']
                                ax.bar(pre_data.index, pre_data['Volume'], color='blue', alpha=0.6, label='Pre-Event')
                                
                                # Plot post-event volume
                                post_data = impact_result['post_event_data']
                                ax.bar(post_data.index, post_data['Volume'], color='green', alpha=0.6, label='Post-Event')
                                
                                # Add event line
                                ax.axvline(x=event_date, color='red', linestyle='--', linewidth=2, alpha=0.8)
                                
                                # Add labels and legend
                                ax.set_title(f"Volume Before and After {event_name} ({ticker})", fontsize=14)
                                ax.set_xlabel("Date", fontsize=12)
                                ax.set_ylabel("Volume", fontsize=12)
                                ax.grid(alpha=0.3)
                                ax.legend()
                                
                                # Format x-axis
                                plt.xticks(rotation=45)
                                plt.tight_layout()
                                
                                st.pyplot(vol_fig)
                            
                            with stats_tab:
                                st.subheader("Statistical Analysis")
                                
                                # Display volatility metrics
                                vol_col1, vol_col2 = st.columns(2)
                                
                                with vol_col1:
                                    pre_vol = impact_result['returns_metrics'].get('pre_return_volatility', None)
                                    if pre_vol is not None:
                                        st.metric("Pre-Event Volatility", f"{pre_vol:.4f}")
                                    else:
                                        st.info("Pre-Event Volatility: Not available")
                                    
                                with vol_col2:
                                    post_vol = impact_result['returns_metrics'].get('post_return_volatility', None)
                                    vol_change_pct = impact_result['returns_metrics'].get('volatility_change_pct', None)
                                    
                                    if post_vol is not None:
                                        delta = f"{vol_change_pct:.2f}%" if vol_change_pct is not None else None
                                        st.metric("Post-Event Volatility", f"{post_vol:.4f}", delta=delta)
                                    else:
                                        st.info("Post-Event Volatility: Not available")
                                
                                # Display significance test results
                                st.subheader("Statistical Significance")
                                stat_test = impact_result.get('statistical_test', {})
                                
                                if 'error' in stat_test:
                                    st.warning(f"Statistical test error: {stat_test['error']}")
                                else:
                                    p_value = stat_test.get('p_value', None)
                                    t_stat = stat_test.get('t_statistic', None)
                                    is_significant = stat_test.get('is_significant', False)
                                    
                                    if p_value is not None and t_stat is not None:
                                        sig_col1, sig_col2 = st.columns(2)
                                        
                                        with sig_col1:
                                            st.metric("T-Statistic", f"{t_stat:.4f}")
                                            
                                        with sig_col2:
                                            st.metric("P-Value", f"{p_value:.4f}")
                                        
                                        if is_significant:
                                            st.success("The difference between pre-event and post-event returns is statistically significant (p < 0.05)")
                                        else:
                                            st.info("The difference between pre-event and post-event returns is not statistically significant")
                                    else:
                                        st.info("Statistical significance test results are not available")
                                
                                # Show data used for analysis
                                with st.expander("View Daily Returns Data", expanded=False):
                                    all_data = pd.concat([
                                        impact_result['pre_event_data'][['Close', 'Daily Return']],
                                        impact_result['post_event_data'][['Close', 'Daily Return']]
                                    ])
                                    
                                    # Add period column
                                    all_data['Period'] = 'Pre-Event'
                                    all_data.loc[impact_result['post_event_data'].index, 'Period'] = 'Post-Event'
                                    
                                    st.dataframe(all_data)
                            
                            # Provide a download option
                            st.subheader("Download Results")
                            
                            # Create CSV data
                            pre_data = impact_result['pre_event_data'].copy()
                            pre_data['Period'] = 'Pre-Event'
                            
                            post_data = impact_result['post_event_data'].copy()
                            post_data['Period'] = 'Post-Event'
                            
                            combined_data = pd.concat([pre_data, post_data])
                            
                            # Add event markers
                            combined_data['Event'] = ''
                            combined_data.loc[combined_data.index == impact_result['event_date'], 'Event'] = event_name
                            
                            csv_data = combined_data.to_csv(index=True)
                            
                            download_filename = f"{ticker}_{event_name.replace(' ', '_')}_{date_str}_analysis.csv"
                            st.download_button(
                                label="Download Analysis Data as CSV",
                                data=csv_data,
                                file_name=download_filename,
                                mime="text/csv"
                            )
            except Exception as e:
                st.error(f"Error in event impact analysis: {str(e)}")
        else:
            st.error("Please enter both ticker symbol and event date")

def display_grouped_analysis_page():
    """
    Display the grouped analysis page for analyzing multiple trials grouped by sponsor or disease.
    This allows users to see trends across groups of related trials.
    """
    st.header("Grouped Trial Analysis")
    
    st.write("""
    This tool analyzes groups of related clinical trials to identify patterns and correlations
    across multiple studies with the same sponsor or targeting the same disease.
    """)
    
    # Check if we have studies to analyze
    if st.session_state.current_results is None or len(st.session_state.current_results) < 2:
        st.warning("Insufficient data for grouped analysis. Please search for at least 2 clinical trials first.")
        
        if st.button("Go to Search Page"):
            st.session_state.page = "search"
            st.rerun()
        
        return
    
    # Create selection for grouping method
    grouping_method = st.radio(
        "Group Trials By:",
        ["Sponsor-Disease Pairs"],
        horizontal=True,
        help="Clinical trials are grouped by sponsor and disease combinations"
    )
    
    # Get the studies
    studies = st.session_state.current_results
    
    # Filter studies to include only those with financial data
    financial_studies = [study for study in studies if study.get('has_financial_data', False)]
    
    if len(financial_studies) < 2:
        st.warning("Insufficient data for grouped analysis. At least 2 studies with financial data are needed.")
        return
    
    # Group the trials using the finance module
    with st.spinner("Grouping trials and analyzing patterns..."):
        grouped_trials = fin.group_trials_by_sponsor_disease(financial_studies)
    
    # Display number of groups found
    st.success(f"Found {len(grouped_trials)} groups of related trials")
    
    # Display each group in an expander
    for group_key, group_data in grouped_trials.items():
        sponsor, condition = group_key  # Unpack the tuple key
        trials = group_data.get("trials", [])
        
        with st.expander(f"{sponsor} - {condition} ({len(trials)} trials)"):
            # Display group summary
            st.markdown(f"### {sponsor} researching {condition}")
            
            # Show metadata about the group
            metadata = {
                "Total trials": len(trials),
                "Sponsor": group_data.get('sponsor', 'N/A'),
                "Condition": group_data.get('condition', 'N/A'),
                "Ticker": group_data.get('ticker', 'N/A')
            }
            
            # Create a DataFrame for the metadata
            metadata_df = pd.DataFrame(list(metadata.items()), columns=["Metric", "Value"])
            st.table(metadata_df)
            
            # Create a table of the trials in this group
            cols = ["nct_id", "brief_title", "phase", "status"]
            
            trial_data = [{col: trial.get(col, "N/A") for col in cols} for trial in trials]
            trials_df = pd.DataFrame(trial_data)
            st.dataframe(trials_df)
            
            # Show financial impact analysis
            ticker = group_data.get('ticker')
            if ticker:
                st.markdown("### Financial Impact Analysis")
                
                if st.button("Analyze Financial Impact", key=f"finance_{sponsor}_{condition}"):
                    with st.spinner(f"Analyzing financial impact for {ticker}..."):
                        # Calculate impact metrics for the group
                        impact_data = fin.analyze_grouped_trials_impact(
                            grouped_trials={group_key: group_data},
                            window_days=15  # 15 days before/after key dates
                        )
                        
                        if group_key in impact_data:
                            group_impact = impact_data[group_key]
                            
                            # Display impact metrics
                            metric_cols = st.columns(4)
                            
                            with metric_cols[0]:
                                st.metric(
                                    "Avg Price Change", 
                                    f"{group_impact.get('avg_price_change_pct', 0):.2f}%"
                                )
                            
                            with metric_cols[1]:
                                st.metric(
                                    "Avg Volume Change", 
                                    f"{group_impact.get('avg_volume_change_pct', 0):.2f}%"
                                )
                            
                            with metric_cols[2]:
                                st.metric(
                                    "Volatility Impact", 
                                    f"{group_impact.get('volatility_impact', 0):.2f}%"
                                )
                            
                            with metric_cols[3]:
                                sentiment = group_impact.get('sentiment', 'Neutral')
                                st.metric("Market Sentiment", sentiment)
                            
                            # Show event timeline
                            st.subheader("Trial Events Timeline")
                            event_data = group_impact.get('event_impacts', [])
                            if event_data:
                                # Extract key information from each event impact
                                event_summary = []
                                for event in event_data:
                                    event_summary.append({
                                        "Event Type": event.get('event_type', 'Unknown'),
                                        "NCT ID": event.get('nct_id', 'N/A'),
                                        "Date": event.get('date_str', 'N/A'),
                                        "Pre-Event Change": f"{event.get('price_metrics', {}).get('pre_window_change_pct', 0):.2f}%",
                                        "Post-Event Change": f"{event.get('price_metrics', {}).get('post_window_change_pct', 0):.2f}%",
                                        "Event Day Change": f"{event.get('price_metrics', {}).get('event_day_change_pct', 0):.2f}%"
                                    })
                                
                                if event_summary:
                                    events_df = pd.DataFrame(event_summary)
                                    st.dataframe(events_df)
                                    
                            else:
                                st.info("No event timeline data available")
                            
                            # Generate and display LLM analysis if available
                            if 'llm_analysis' in group_impact:
                                st.markdown("### AI Analysis")
                                st.markdown(group_impact['llm_analysis'])
                        else:
                            st.error(f"No impact data found for group: {sponsor} - {condition}")
            
            # Show trial phase distribution
            phases = [t.get("phase", "N/A") for t in trials]
            phase_counts = {}
            for phase in phases:
                if phase == "N/A":
                    phase = "Unknown"
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
            
            st.markdown("### Trial Phase Distribution")
            st.bar_chart(phase_counts)
            
            # Show status distribution
            statuses = [t.get("status", "N/A") for t in trials]
            status_counts = {}
            for status in statuses:
                if status == "N/A":
                    status = "Unknown"
                status_counts[status] = status_counts.get(status, 0) + 1
            
            st.markdown("### Trial Status Distribution")
            st.bar_chart(status_counts)

def main():
    """Main application function"""
    
    # Set wide mode
    st.set_page_config(
        page_title="Clinical Trial Stock Analyzer",
        page_icon="💊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Add custom CSS for better styling
    st.markdown("""
    <style>
    .big-font {
        font-size:24px !important;
        font-weight: bold;
    }
    .highlight {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .ticker {
        color: #0078ff;
        font-weight: bold;
    }
    .positive {
        color: green;
    }
    .negative {
        color: red;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Application title and description
    st.title("Clinical Trial Stock Analyzer")
    
    # Initialize session state to store data between reruns
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    
    if 'saved_studies' not in st.session_state:
        st.session_state.saved_studies = []
    
    if 'current_results' not in st.session_state:
        st.session_state.current_results = None
    
    if 'current_results_df' not in st.session_state:
        st.session_state.current_results_df = None
    
    if 'last_search_params' not in st.session_state:
        st.session_state.last_search_params = None
    
    if 'llm_analysis' not in st.session_state:
        st.session_state.llm_analysis = None
    
    if 'page' not in st.session_state:
        st.session_state.page = "search"
    
    if 'stock_data_cache' not in st.session_state:
        st.session_state.stock_data_cache = {}
        
    # Define the navigation bar
    st.sidebar.title("Navigation")
    pages = {
        "search": "🔍 Trial Search", 
        "analysis": "📊 Analysis Dashboard", 
        "saved": "💾 Saved Studies",
        "trial_stock": "📈 Trial-Stock Correlation",
        "event_impact": "⚡ Event Impact Analyzer",
        "grouped_analysis": "🔬 Grouped Trial Analysis"
    }
    
    # Navigation bar
    selected_page = st.sidebar.radio("Go to", list(pages.values()))
    
    # Map selected value back to the key
    for key, value in pages.items():
        if value == selected_page:
            st.session_state.page = key
    
    # Content based on selected page
    if st.session_state.page == "search":
        # Search page for querying clinical trials
        display_search_page()
    elif st.session_state.page == "analysis":
        # Analysis page for reviewing results
        if st.session_state.current_results_df is not None:
            display_analysis_page()
        else:
            st.warning("Please run a search first to see analysis results.")
            display_search_page()
    elif st.session_state.page == "saved":
        # Saved studies page
        display_saved_studies_page()
    elif st.session_state.page == "trial_stock":
        # Trial-stock correlation page
        display_trial_stock_analysis_page()
    elif st.session_state.page == "event_impact":
        # New page for event impact analysis
        display_trial_event_impact_page()
    elif st.session_state.page == "grouped_analysis":
        # New page for grouped trial analysis
        display_grouped_analysis_page()

if __name__ == "__main__":
    main() 