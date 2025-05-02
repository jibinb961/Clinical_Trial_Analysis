import streamlit as st
import datetime
import pandas as pd

# Import from our modules
import data_module as data
import llm_module as llm

# Set page configuration
st.set_page_config(
    page_title="Clinical Trial Focus Analyzer",
    page_icon="💊",
    layout="wide"
)

def format_date(date_str):
    """
    Format date strings from the API into a more readable format.
    
    Args:
        date_str: Date string in ISO 8601 format (yyyy, yyyy-MM, yyyy-MM-dd)
        
    Returns:
        Formatted date string or original if formatting fails
    """
    if not date_str:
        return "N/A"
        
    try:
        # Handle different ISO 8601 formats
        if len(date_str) == 4:  # yyyy
            return date_str
        elif len(date_str) == 7:  # yyyy-MM
            year, month = date_str.split('-')
            month_name = datetime.date(1900, int(month), 1).strftime('%B')
            return f"{month_name} {year}"
        elif len(date_str) >= 10:  # yyyy-MM-dd or longer
            date_obj = datetime.datetime.strptime(date_str[:10], '%Y-%m-%d')
            return date_obj.strftime('%b %d, %Y')
        else:
            return date_str
    except Exception:
        return date_str

def main():
    """Main application function"""
    
    # Header section
    st.title("Clinical Trial Focus Analyzer")
    st.subheader("Discover what pharmaceutical companies are focusing on in clinical research")
    
    st.markdown("""
    This tool analyzes a company's recent clinical trials to identify research trends and focus areas.
    Enter a stock ticker, select a date range, and get AI-powered insights into the company's clinical pipeline.
    """)
    
    st.markdown("---")
    
    # Input section
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        ticker = st.text_input("Stock Ticker Symbol", "PFE", help="Enter a pharmaceutical company ticker symbol (e.g., PFE for Pfizer)")
        
        # Add sorting options
        sort_options = {
            "enrollment": "Enrollment (Largest First)",
            "start_date": "Start Date (Newest First)",
            "completion_date": "Completion Date (Soonest First)"
        }
        sort_by = st.selectbox(
            "Sort Trials By",
            options=list(sort_options.keys()),
            format_func=lambda x: sort_options[x],
            help="Choose how to sort the clinical trials"
        )
    
    with col2:
        # Date range picker
        today = datetime.date.today()
        four_years_ago = today.replace(year=today.year - 4)
        
        date_cols = st.columns(2)
        with date_cols[0]:
            start_date = st.date_input("Start Date", four_years_ago, 
                                      help="Find trials active after this date")
        with date_cols[1]:
            end_date = st.date_input("End Date", today,
                                    help="Find trials active before this date")
    
    with col3:
        max_trials = st.number_input("Max Trials to Analyze", 
                                    min_value=5, max_value=20, value=10,
                                    help="Maximum number of trials to include in the analysis")
        
        # Add an advanced options expander
        with st.expander("Date Filter Information"):
            st.markdown("""
            The date filter finds trials that were active during the selected period by:
            - Including trials that started on or before the end date, AND
            - Including trials that either:
              - Have no completion date (ongoing), OR
              - Have a completion date on or after the start date
            
            This filtering is performed client-side on trial data retrieved from ClinicalTrials.gov API, 
            ensuring you see trials that were ongoing during your selected date range.
            
            Note: The date filter handles all ISO 8601 date formats returned by the API: year (yyyy), 
            year-month (yyyy-MM), and full dates (yyyy-MM-dd).
            """)
    
    # Validate inputs
    if start_date > end_date:
        st.error("Error: Start date must be before end date")
        return
    
    # Analysis button
    analyze_button = st.button("Analyze Sponsor Focus", use_container_width=True)
    
    # Process when button is clicked
    if analyze_button:
        # Convert ticker to sponsor name
        sponsor_name = data.map_ticker_to_sponsor(ticker)
        
        if not sponsor_name:
            st.error(f"Could not map ticker '{ticker}' to a sponsor company. Please check the ticker symbol.")
            return
            
        # Show processing status
        with st.spinner(f"Fetching and analyzing clinical trials for {sponsor_name}..."):
            # Process the trials
            trials = data.process_trials_for_analysis(
                sponsor_name, 
                start_date, 
                end_date,
                max_trials,
                sort_by
            )
            
            if not trials:
                st.warning(f"No clinical trials found for {sponsor_name} in the selected date range.")
                return
                
            # Show number of trials
            st.success(f"Found {len(trials)} clinical trials for {sponsor_name} between {start_date} and {end_date}")
            
            # Generate analysis with Gemini
            analysis = llm.generate_sponsor_analysis(trials, sponsor_name)
            
            # Display analysis and trial data
            st.markdown("## Research Focus Analysis")
            
            # Create tabs for analysis and raw data
            tab1, tab2, tab3 = st.tabs(["AI-Generated Analysis", "Trial Data", "Timeline View"])
            
            with tab1:
                st.markdown(analysis)
                
                # Add citation
                st.markdown("---")
                st.caption("Analysis generated by Google Gemini AI based on ClinicalTrials.gov data")
            
            with tab2:
                # Convert to DataFrame for display
                df = pd.DataFrame(trials)
                
                # Format dates for display
                for date_col in ['start_date', 'primary_completion_date', 'completion_date', 'last_update_date']:
                    if date_col in df.columns:
                        df[f'{date_col}_display'] = df[date_col].apply(format_date)
                
                # Display key columns first
                display_cols = [
                    'nct_id', 'brief_title', 'conditions', 'phase', 
                    'status', 'enrollment', 'start_date_display', 
                    'primary_completion_date_display', 'completion_date_display'
                ]
                
                # Ensure all columns exist
                display_cols = [col for col in display_cols if col in df.columns]
                
                # Create a display DataFrame with readable column headers
                display_df = df[display_cols].copy()
                if 'start_date_display' in display_df.columns:
                    display_df = display_df.rename(columns={
                        'start_date_display': 'Start Date',
                        'primary_completion_date_display': 'Primary Completion',
                        'completion_date_display': 'Completion Date',
                        'nct_id': 'NCT ID',
                        'brief_title': 'Title',
                        'conditions': 'Conditions',
                        'phase': 'Phase',
                        'status': 'Status',
                        'enrollment': 'Enrollment'
                    })
                
                # Display the data
                st.dataframe(display_df, use_container_width=True)
                
                # Display sort explanation
                if sort_by == "enrollment":
                    st.caption("Trials sorted by enrollment size (largest first)")
                elif sort_by == "start_date":
                    st.caption("Trials sorted by start date (newest first)")
                else:
                    st.caption("Trials sorted by completion date (soonest first)")
                
                # Download option (include original data)
                export_cols = [
                    'nct_id', 'brief_title', 'conditions', 'phase', 
                    'status', 'enrollment', 'start_date', 
                    'primary_completion_date', 'completion_date', 
                    'last_update_date'
                ]
                export_cols = [col for col in export_cols if col in df.columns]
                export_df = df[export_cols].copy()
                
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="Download Trial Data as CSV",
                    data=csv,
                    file_name=f"{sponsor_name}_trials_{start_date}_to_{end_date}.csv",
                    mime="text/csv",
                )
            
            with tab3:
                # Create a timeline view of the trials
                if 'start_date' in df.columns and df['start_date'].notna().any():
                    st.subheader("Trial Timeline")
                    
                    # Create a timeline chart showing start and completion dates
                    timeline_data = []
                    
                    for _, trial in df.iterrows():
                        # Only include trials with at least a start date
                        if pd.notna(trial.get('start_date')):
                            timeline_item = {
                                'NCT ID': trial.get('nct_id', 'N/A'),
                                'Title': trial.get('brief_title', 'N/A'),
                                'Phase': trial.get('phase', 'N/A'),
                                'Start': format_date(trial.get('start_date')),
                                'End': format_date(trial.get('completion_date')) if pd.notna(trial.get('completion_date')) else 'Ongoing',
                                'Status': trial.get('status', 'N/A')
                            }
                            timeline_data.append(timeline_item)
                    
                    # Display timeline data
                    if timeline_data:
                        timeline_df = pd.DataFrame(timeline_data)
                        st.dataframe(timeline_df, use_container_width=True)
                    else:
                        st.info("No timeline data available for these trials.")
                else:
                    st.info("Timeline view requires trials with start dates.")

# Add explanatory info in sidebar
st.sidebar.title("About this Tool")
st.sidebar.markdown("""
This is a simplified version of the Clinical Trial - Stock Correlation analyzer.

### How it works:
1. Enter a stock ticker symbol for a pharmaceutical company
2. Select a date range to filter clinical trials
3. Click "Analyze" to retrieve clinical trial data
4. AI summarizes the company's research focus

### Data Sources:
- ClinicalTrials.gov API (for trial data)
- Google Gemini AI (for analysis)
""")

# Add API information in sidebar
st.sidebar.markdown("---")
st.sidebar.title("API Details")
st.sidebar.markdown("""
This tool uses the ClinicalTrials.gov API v2 to find trials:
- Retrieves trials by sponsor name
- Applies client-side date filtering to find trials active during selected period
- Handles structured date fields from the API (startDateStruct, completionDateStruct)
- Processes dates in various ISO 8601 formats (year, year-month, full dates)
""")

# Add data disclaimer
st.sidebar.markdown("---")
st.sidebar.caption("""
**Disclaimer**: This tool provides research insights for informational 
purposes only. It should not be used for investment decisions or medical advice.
""")

if __name__ == "__main__":
    main() 