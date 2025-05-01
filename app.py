import streamlit as st
import pandas as pd
import os
import time
import datetime
import json
import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import google.generativeai as genai
from dotenv import load_dotenv
import finance_module as fin

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
LEGACY_API_URL = "https://clinicaltrials.gov/api/legacy/full-studies"
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

def fetch_clinical_trials(search_term: str, min_rank: int, max_rank: int) -> Optional[Dict]:
    """
    Fetch clinical trial data from ClinicalTrials.gov API using the legacy endpoint.
    According to documentation, the legacy endpoint supports the same parameters as classic.
    
    Args:
        search_term: The search term to query
        min_rank: The starting rank of results
        max_rank: The ending rank of results
        
    Returns:
        Dict containing the API response or None if the request failed
    """
    try:
        # XML is the only supported format for legacy endpoint according to documentation
        params = {
            "expr": search_term,
            "min_rnk": min_rank,
            "max_rnk": max_rank,
            "fmt": "xml"
        }
        
        with st.spinner(f"Fetching studies {min_rank}-{max_rank} for '{search_term}'..."):
            # Make the request without verbose logging
            response = requests.get(LEGACY_API_URL, params=params)
            
            if response.status_code == 200:
                return {"xml_content": response.text}
            else:
                st.error(f"API request failed with status code: {response.status_code}")
                
                # Display more detailed error info
                try:
                    error_content = response.text[:500] + "..." if len(response.text) > 500 else response.text
                    st.error(f"Error response content: {error_content}")
                except:
                    st.error("Could not extract error content from response")
                
                # Try with simpler parameters as fallback
                if min_rank > 1 or max_rank > 100:
                    st.info("Trying with reduced result set (1-10)...")
                    simple_params = {
                        "expr": search_term,
                        "min_rnk": 1,
                        "max_rnk": 10,
                        "fmt": "xml"
                    }
                    response = requests.get(LEGACY_API_URL, params=simple_params)
                    if response.status_code == 200:
                        st.success("Simplified request succeeded. Only returning first 10 results.")
                        return {"xml_content": response.text}
                
                return None
    except Exception as e:
        st.error(f"Error fetching clinical trials: {str(e)}")
        return None

def dump_element_structure(element, level=0, path="", max_level=4):
    """Recursively dump the structure of an XML element for debugging."""
    if level > max_level:
        return f"{' ' * level}..."
    
    if element is None:
        return f"{' ' * level}None"
    
    current_path = f"{path}/{element.tag}" if path else element.tag
    result = [f"{' ' * level}{current_path} = {element.text and element.text.strip()[:50]}"]
    
    for child in element:
        result.append(dump_element_structure(child, level + 2, current_path, max_level))
    
    return "\n".join(result)

def parse_xml_response(xml_content: str) -> List[Dict]:
    """
    Parse XML response from ClinicalTrials.gov API based on the actual structure from sample data.
    
    Args:
        xml_content: XML response from the API
        
    Returns:
        List of dictionaries containing extracted trial data
    """
    try:
        # Parse XML
        root = ET.fromstring(xml_content)
        studies = []
        
        # Get study counts but don't display yet
        study_count_found = 0
        study_count_elem = root.find(".//NStudiesFound")
        if study_count_elem is not None:
            study_count_found = int(study_count_elem.text)
        
        # Find all FullStudy elements
        full_studies = root.findall(".//FullStudy")
        
        # Process each FullStudy element (without verbose debug info)
        for i, full_study in enumerate(full_studies):
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
                    'brief_summary': 'N/A'
                }
                
                # Find the Study struct - this is always the parent element
                study_struct = full_study.find("./Struct[@Name='Study']")
                
                if study_struct is not None:
                    # Find the ProtocolSection struct - this contains all the study details
                    protocol_section = study_struct.find("./Struct[@Name='ProtocolSection']")
                    
                    if protocol_section is not None:
                        # Extract NCT ID (always in IdentificationModule)
                        id_module = protocol_section.find("./Struct[@Name='IdentificationModule']")
                        if id_module is not None:
                            nct_id = id_module.find("./Field[@Name='NCTId']")
                            if nct_id is not None and nct_id.text:
                                study_data['nct_id'] = nct_id.text
                            
                            brief_title = id_module.find("./Field[@Name='BriefTitle']")
                            if brief_title is not None and brief_title.text:
                                study_data['brief_title'] = brief_title.text
                        
                        # Extract Brief Summary (in DescriptionModule)
                        desc_module = protocol_section.find("./Struct[@Name='DescriptionModule']")
                        if desc_module is not None:
                            brief_summary = desc_module.find("./Field[@Name='BriefSummary']")
                            if brief_summary is not None and brief_summary.text:
                                study_data['brief_summary'] = brief_summary.text
                        
                        # Extract Phase (in DesignModule > PhaseList > Phase)
                        design_module = protocol_section.find("./Struct[@Name='DesignModule']")
                        if design_module is not None:
                            phase_list = design_module.find("./List[@Name='PhaseList']")
                            if phase_list is not None:
                                phase = phase_list.find("./Field[@Name='Phase']")
                                if phase is not None and phase.text:
                                    study_data['phase'] = phase.text
                            
                            # Extract Enrollment (in DesignModule > EnrollmentInfo > EnrollmentCount)
                            enrollment_info = design_module.find("./Struct[@Name='EnrollmentInfo']")
                            if enrollment_info is not None:
                                enrollment_count = enrollment_info.find("./Field[@Name='EnrollmentCount']")
                                if enrollment_count is not None and enrollment_count.text:
                                    study_data['enrollment'] = enrollment_count.text
                        
                        # Extract Conditions (in ConditionsModule > ConditionList > Condition)
                        conditions_module = protocol_section.find("./Struct[@Name='ConditionsModule']")
                        if conditions_module is not None:
                            condition_list = conditions_module.find("./List[@Name='ConditionList']")
                            if condition_list is not None:
                                conditions = []
                                for condition in condition_list.findall("./Field[@Name='Condition']"):
                                    if condition.text:
                                        conditions.append(condition.text)
                                if conditions:
                                    study_data['conditions'] = ", ".join(conditions)
                        
                        # Extract Interventions (in ArmsInterventionsModule > InterventionList > Intervention)
                        arms_module = protocol_section.find("./Struct[@Name='ArmsInterventionsModule']")
                        if arms_module is not None:
                            intervention_list = arms_module.find("./List[@Name='InterventionList']")
                            if intervention_list is not None:
                                interventions = []
                                for intervention_struct in intervention_list.findall("./Struct[@Name='Intervention']"):
                                    int_type = intervention_struct.find("./Field[@Name='InterventionType']")
                                    int_name = intervention_struct.find("./Field[@Name='InterventionName']")
                                    
                                    if int_name is not None and int_name.text:
                                        if int_type is not None and int_type.text:
                                            interventions.append(f"{int_type.text}: {int_name.text}")
                                        else:
                                            interventions.append(int_name.text)
                                
                                if not interventions:
                                    # Try ArmGroupList as fallback
                                    arm_group_list = arms_module.find("./List[@Name='ArmGroupList']")
                                    if arm_group_list is not None:
                                        for arm in arm_group_list.findall("./Struct[@Name='ArmGroup']"):
                                            arm_label = arm.find("./Field[@Name='ArmGroupLabel']")
                                            arm_type = arm.find("./Field[@Name='ArmGroupType']")
                                            
                                            if arm_label is not None and arm_label.text:
                                                if arm_type is not None and arm_type.text:
                                                    interventions.append(f"Arm: {arm_label.text} ({arm_type.text})")
                                                else:
                                                    interventions.append(f"Arm: {arm_label.text}")
                                
                                if interventions:
                                    study_data['interventions'] = "; ".join(interventions)
                        
                        # Extract Sponsor (in SponsorCollaboratorsModule > LeadSponsor > LeadSponsorName)
                        sponsor_module = protocol_section.find("./Struct[@Name='SponsorCollaboratorsModule']")
                        if sponsor_module is not None:
                            lead_sponsor = sponsor_module.find("./Struct[@Name='LeadSponsor']")
                            if lead_sponsor is not None:
                                sponsor_name = lead_sponsor.find("./Field[@Name='LeadSponsorName']")
                                if sponsor_name is not None and sponsor_name.text:
                                    study_data['sponsor'] = sponsor_name.text
                        
                        # Extract Primary Outcome (in OutcomesModule > PrimaryOutcomeList > PrimaryOutcome > PrimaryOutcomeMeasure)
                        outcomes_module = protocol_section.find("./Struct[@Name='OutcomesModule']")
                        if outcomes_module is not None:
                            primary_outcome_list = outcomes_module.find("./List[@Name='PrimaryOutcomeList']")
                            if primary_outcome_list is not None:
                                primary_outcome = primary_outcome_list.find("./Struct[@Name='PrimaryOutcome']")
                                if primary_outcome is not None:
                                    outcome_measure = primary_outcome.find("./Field[@Name='PrimaryOutcomeMeasure']")
                                    if outcome_measure is not None and outcome_measure.text:
                                        study_data['primary_outcome'] = outcome_measure.text
                
                # Only add studies that have a valid NCT ID
                if study_data['nct_id'] != 'N/A':
                    # Create a concise summary string for this study
                    study_data['concise_summary'] = create_concise_summary(study_data)
                    studies.append(study_data)
                else:
                    st.warning(f"Skipping study {i+1} with no NCT ID")
            except Exception as e:
                st.warning(f"Error parsing individual study {i+1}: {str(e)}")
                continue
        
        # Display a single line with study counts
        if study_count_found > 0:
            st.info(f"Found {study_count_found} studies in total, extracted {len(studies)} studies for analysis.")
        
        return studies
    except Exception as e:
        st.error(f"Error parsing XML response: {str(e)}")
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
    
    # Create the summary string
    summary = f"NCT ID: {study_data['nct_id']}, Title: {study_data['brief_title']}, "
    summary += f"Phase: {study_data['phase']}, Enrollment: {enrollment}, "
    summary += f"Main Intervention: {main_intervention}, Primary Outcome: {study_data['primary_outcome']}, "
    summary += f"Sponsor: {study_data['sponsor']}, Condition: {study_data['conditions']}"
    
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

def process_clinical_trials(search_term: str, num_studies: int) -> Dict:
    """
    Process clinical trials data by fetching from API and parsing XML.
    Now with batch LLM analysis instead of per-study analysis.
    
    Args:
        search_term: The search term to query
        num_studies: Number of studies to retrieve
        
    Returns:
        Dictionary containing processed results and analysis
    """
    # Warn if trying to retrieve more than the API allows
    if num_studies > MAX_RETRIEVABLE_STUDIES:
        st.warning(f"The API only allows retrieving the first {MAX_RETRIEVABLE_STUDIES} studies. Limiting to this number.")
        num_studies = MAX_RETRIEVABLE_STUDIES
    
    all_studies = []
    total_batches = (num_studies + MAX_RESULTS_PER_PAGE - 1) // MAX_RESULTS_PER_PAGE
    
    # Create progress indicators
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    processed_count = 0
    
    # Process in batches to respect API limits
    for batch in range(total_batches):
        min_rank = batch * MAX_RESULTS_PER_PAGE + 1
        max_rank = min(min_rank + MAX_RESULTS_PER_PAGE - 1, num_studies)
        
        status_text.text(f"Fetching batch {batch+1}/{total_batches} (studies {min_rank}-{max_rank})...")
        
        # Fetch data from API
        api_response = fetch_clinical_trials(search_term, min_rank, max_rank)
        
        if not api_response:
            st.warning(f"Failed to fetch batch {batch+1}. Continuing with next batch...")
            continue
        
        # Parse XML response if present
        studies = []
        if "xml_content" in api_response:
            studies = parse_xml_response(api_response["xml_content"])
        
        # Add studies to our collection (without verbose logging)
        all_studies.extend(studies)
        processed_count += len(studies)
        progress_bar.progress(min(processed_count / num_studies, 1.0))
        
        # If we've processed enough studies, break
        if processed_count >= num_studies:
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
        "search_term": search_term,
        "studies_found": len(enriched_studies)
    }

def display_detailed_results(results_df):
    """Display detailed results for each study in expandable sections."""
    st.subheader("Detailed Results")
    
    for i, row in results_df.iterrows():
        with st.expander(f"{row['nct_id']}: {row['brief_title']}"):
            # Remove fields not needed for display
            display_fields = ['nct_id', 'brief_title', 'phase', 'enrollment', 
                             'conditions', 'interventions', 'sponsor', 
                             'primary_outcome']
            display_row = {k: v for k, v in row.items() if k in display_fields}
            
            # Create tabs for different types of information
            tab1, tab2 = st.tabs(["Trial Information", "Market Analysis"])
            
            # Tab 1: Trial Information
            with tab1:
                # Display as two columns
                cols = st.columns(2)
                for j, (key, value) in enumerate(display_row.items()):
                    col_idx = j % 2
                    with cols[col_idx]:
                        st.markdown(f"**{key.replace('_', ' ').title()}**: {value}")
                
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

def main():
    st.set_page_config(page_title="Clinical Trial Analyzer", page_icon="🧬", layout="wide")
    
    st.title("Clinical Trial Analyzer")
    st.markdown("""
    Search and analyze clinical trials from ClinicalTrials.gov using AI.
    """)
    
    # Sidebar with usage instructions
    with st.sidebar:
        st.header("Instructions")
        st.markdown("""
        1. Enter a search term (e.g., "diabetes", "cancer", "covid", "remdesivir")
        2. Specify the number of studies to retrieve (max 1000)
        3. Click "Search and Analyze"
        4. Results will be displayed along with AI-generated insights
        """)
        
        st.header("About")
        st.markdown("""
        This application uses:
        - ClinicalTrials.gov API to retrieve clinical trial data
        - Gemini AI to analyze trends and generate insights
        - Streamlit for the user interface
        - yfinance for financial data analysis
        
        Note: Processing large numbers of trials may take time due to API rate limits.
        """)
    
    # Search inputs
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_term = st.text_input("Search Term", "diabetes")
    
    with col2:
        num_studies = st.number_input("Number of Studies", 
                                      min_value=1, 
                                      max_value=MAX_ALLOWED_STUDIES, 
                                      value=DEFAULT_NUM_STUDIES)
    
    # Search button
    if st.button("Search and Analyze"):
        if not search_term:
            st.error("Please enter a search term.")
        else:
            # Process clinical trials
            results = process_clinical_trials(search_term, num_studies)
            
            if results["studies"]:
                # Display AI-generated insights
                st.subheader("AI Analysis and Insights")
                insights_container = st.container()
                with insights_container:
                    st.markdown("---")
                    if "error" in results["analysis"] and results["analysis"]["error"] != "":
                        st.warning(results["analysis"]["error"])
                    st.markdown(results["analysis"]["insights"])
                    st.markdown("---")
                    st.caption(f"Analysis based on {results['analysis']['studies_analyzed']} studies | Generated: {results['analysis'].get('time_generated', 'Not available')}")
                
                # Create DataFrame from results
                studies = results["studies"]
                df = pd.DataFrame(studies)
                
                # Display a summary of processing results
                st.subheader("Processing Summary")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Studies Found", len(studies))
                with col2:
                    st.metric("Search Term", search_term)
                with col3:
                    # Count studies with financial data
                    financial_studies = sum(1 for study in studies if study.get('has_financial_data', False))
                    st.metric("Studies with Financial Data", financial_studies)
                
                # Display results table
                st.subheader("Extracted Information")
                
                # Add financial data columns if present
                display_cols = ['nct_id', 'brief_title', 'phase', 'enrollment', 
                               'conditions', 'interventions', 'sponsor', 
                               'primary_outcome']
                
                # Add financial columns if they exist
                if 'ticker' in df.columns:
                    display_cols.append('ticker')
                
                # Create display dataframe
                display_df = df[display_cols]
                
                # Add option to show/hide financial data
                show_financial = st.checkbox("Show Financial Impact", value=True)
                
                if show_financial:
                    # Create a filtered view with only financially analyzable trials
                    if 'has_financial_data' in df.columns:
                        financial_df = df[df['has_financial_data'] == True]
                        if not financial_df.empty:
                            st.subheader("Financial Impact Overview")
                            st.dataframe(financial_df[display_cols], use_container_width=True)
                
                # Show all trials
                st.subheader("All Clinical Trials")
                st.dataframe(display_df, use_container_width=True)
                
                # Display detailed results for each file
                display_detailed_results(df)
                
                # Download buttons for CSV
                st.subheader("Download Options")
                
                # Prepare financial metrics for export
                export_df = display_df.copy()
                
                # Add financial metrics if they exist
                if 'has_financial_data' in df.columns and 'market_metrics' in df.columns:
                    # Extract financial metrics into separate columns
                    financial_rows = df[df['has_financial_data'] == True]
                    
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
                st.download_button(
                    label="Download Results as CSV",
                    data=csv,
                    file_name=f"clinical_trial_analysis_{search_term}_{len(studies)}.csv",
                    mime="text/csv",
                )
                
                # Also download insights as text file
                insights_text = results["analysis"]["insights"]
                st.download_button(
                    label="Download AI Analysis as Text",
                    data=insights_text,
                    file_name=f"clinical_trial_insights_{search_term}_{len(studies)}.txt",
                    mime="text/plain",
                )
                
                # Add watchlist functionality
                st.subheader("Watchlist")
                
                # Check if watchlist exists in session state, initialize if not
                if 'watchlist' not in st.session_state:
                    st.session_state.watchlist = {}
                
                # Get all companies with tickers
                companies_with_tickers = [(study['sponsor'], study['ticker']) 
                                         for study in studies 
                                         if study.get('has_financial_data', False)]
                
                # Remove duplicates by converting to a set and back to list
                unique_companies = list(set(companies_with_tickers))
                
                # Create a selection widget for companies
                if unique_companies:
                    # Create selection box for companies
                    company_options = [f"{company} ({ticker})" for company, ticker in unique_companies]
                    selected_company = st.selectbox("Select company to add to watchlist:", 
                                                   [""] + company_options)
                    
                    if selected_company and st.button("Add to Watchlist"):
                        company_name, ticker = selected_company.split(" (")
                        ticker = ticker.rstrip(")")
                        
                        # Add to watchlist
                        st.session_state.watchlist[ticker] = company_name
                        st.success(f"Added {company_name} ({ticker}) to watchlist")
                
                # Display current watchlist
                if st.session_state.watchlist:
                    st.markdown("### Current Watchlist")
                    watchlist_df = pd.DataFrame({
                        "Company": st.session_state.watchlist.values(),
                        "Ticker": st.session_state.watchlist.keys()
                    })
                    st.dataframe(watchlist_df)
                    
                    # Option to clear watchlist
                    if st.button("Clear Watchlist"):
                        st.session_state.watchlist = {}
                        st.success("Watchlist cleared")
            else:
                st.error("No studies found. Please try a different search term.")
                
                # Provide troubleshooting info
                st.info("""
                Troubleshooting tips:
                1. Try a simpler search term (e.g., use just "diabetes" instead of "type 2 diabetes")
                2. Reduce the number of studies to retrieve
                3. Check that the search term follows the API syntax
                """)

if __name__ == "__main__":
    main() 