import streamlit as st
import datetime
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO

# Import from our modules
import data_module as data
import llm_module as llm

# Set page configuration
st.set_page_config(
    page_title="Clinical Trial Focus Analyzer",
    page_icon="💊",
    layout="wide"
)

# Initialize session state
if 'analyzed_data' not in st.session_state:
    st.session_state.analyzed_data = False
    
if 'analysis_requested' not in st.session_state:
    st.session_state.analysis_requested = False
    
if 'correlation_analysis' not in st.session_state:
    st.session_state.correlation_analysis = ""
    
if 'current_ticker' not in st.session_state:
    st.session_state.current_ticker = ""
    
if 'current_trials' not in st.session_state:
    st.session_state.current_trials = []
    
if 'current_stock_data' not in st.session_state:
    st.session_state.current_stock_data = None

def clear_analysis():
    """Clear the correlation analysis state"""
    st.session_state.analyzed_data = False
    st.session_state.analysis_requested = False
    st.session_state.correlation_analysis = ""

def request_analysis():
    """Mark that analysis has been requested"""
    st.session_state.analysis_requested = True

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

def parse_date_for_stock_analysis(date_str):
    """
    Parse a date string from the API to a datetime object for stock analysis.
    
    Args:
        date_str: Date string in ISO 8601 format (yyyy, yyyy-MM, yyyy-MM-dd)
        
    Returns:
        datetime.datetime object or None if parsing fails
    """
    if not date_str:
        return None
        
    try:
        # Handle different ISO 8601 formats
        if len(date_str) == 4:  # yyyy
            return datetime.datetime.strptime(f"{date_str}-01-01", '%Y-%m-%d')
        elif len(date_str) == 7:  # yyyy-MM
            return datetime.datetime.strptime(f"{date_str}-01", '%Y-%m-%d')
        elif len(date_str) >= 10:  # yyyy-MM-dd or longer
            return datetime.datetime.strptime(date_str[:10], '%Y-%m-%d')
        else:
            return None
    except Exception:
        return None

def get_stock_data(ticker, start_date, end_date):
    """
    Fetch stock price data for a given ticker and date range.
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date for stock data
        end_date: End date for stock data
        
    Returns:
        Pandas DataFrame with stock price data
    """
    try:
        # Add a 30-day buffer before the start date to show pre-period trend
        buffer_start = start_date - datetime.timedelta(days=30)
        # Add a 5-day buffer after the end date for better visualization
        buffer_end = end_date + datetime.timedelta(days=5)
        
        # Set auto_adjust=False to get the Adj Close column
        stock_data = yf.download(ticker, start=buffer_start, end=buffer_end, auto_adjust=False, progress=False)
        
        if stock_data.empty:
            return None
            
        return stock_data
    except Exception as e:
        st.error(f"Error fetching stock data: {str(e)}")
        return None

def plot_stock_with_trials(stock_data, trials, ticker, start_date, end_date):
    """
    Create a plot of stock prices with trial events overlaid.
    
    Args:
        stock_data: DataFrame with stock price data
        trials: List of trial dictionaries
        ticker: Stock ticker symbol
        start_date: Start date for the analysis
        end_date: End date for the analysis
        
    Returns:
        BytesIO object containing the plot image
    """
    if stock_data is None or stock_data.empty:
        return None
        
    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Handle MultiIndex DataFrame (which yfinance sometimes returns)
    is_multiindex = isinstance(stock_data.columns, pd.MultiIndex)
    
    # Plot the stock price (using Adj Close if available, otherwise Close)
    if is_multiindex:
        # For MultiIndex, we need to select the column differently
        if ('Adj Close', ticker) in stock_data.columns:
            price_column = ('Adj Close', ticker)
            price_label = 'Adjusted Close'
        else:
            price_column = ('Close', ticker)
            price_label = 'Close'
        
        # Plot the data
        ax.plot(stock_data.index, stock_data[price_column], label=f'{ticker} Stock Price ({price_label})', color='blue', linewidth=2)
    else:
        # For regular Index
        price_column = 'Adj Close' if 'Adj Close' in stock_data.columns else 'Close'
        price_label = price_column
        ax.plot(stock_data.index, stock_data[price_column], label=f'{ticker} Stock Price ({price_label})', color='blue', linewidth=2)
    
    # Draw vertical lines for trial start dates
    for trial in trials:
        start_date_str = trial.get('start_date')
        if start_date_str:
            trial_date = parse_date_for_stock_analysis(start_date_str)
            if trial_date and trial_date >= stock_data.index[0] and trial_date <= stock_data.index[-1]:
                ax.axvline(x=trial_date, color='red', linestyle='--', alpha=0.7)
                
                # Get the price on the trial date
                try:
                    # Find the nearest date if exact match not found
                    idx = stock_data.index.get_indexer([trial_date], method='nearest')[0]
                    if idx >= 0 and idx < len(stock_data):
                        # Get the price at this index
                        price_on_date = stock_data.iloc[idx][price_column]
                        
                        # For multiindex, price_on_date might still be a Series
                        if isinstance(price_on_date, pd.Series):
                            price_on_date = price_on_date.iloc[0]
                        
                        # Add marker and label
                        ax.plot(trial_date, price_on_date, 'ro', markersize=5)
                        
                        # Add a small label with the trial NCT ID
                        nct_id = trial.get('nct_id', '').split('NCT')[-1]  # Just the number part
                        ax.annotate(f'{nct_id}', 
                                   (trial_date, price_on_date),
                                   xytext=(5, 5),
                                   textcoords='offset points',
                                   fontsize=8,
                                   alpha=0.8)
                except Exception as e:
                    st.warning(f"Could not plot marker for trial {trial.get('nct_id')}: {str(e)}")
    
    # Add vertical lines for analysis period
    ax.axvline(x=start_date, color='green', linestyle='-', alpha=0.5, label='Analysis Start')
    ax.axvline(x=end_date, color='green', linestyle='-', alpha=0.5, label='Analysis End')
    
    # Format the plot
    ax.set_title(f'{ticker} Stock Price with Clinical Trial Events')
    ax.set_xlabel('Date')
    ax.set_ylabel('Stock Price ($)')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    
    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    
    # Save the plot to a BytesIO object
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    
    plt.close(fig)
    return buf

def perform_correlation_analysis():
    """Generate the correlation analysis if requested"""
    if st.session_state.analysis_requested and not st.session_state.analyzed_data:
        # Get the stored data
        ticker = st.session_state.current_ticker
        trials = st.session_state.current_trials
        stock_data = st.session_state.current_stock_data
        start_date = st.session_state.start_date
        end_date = st.session_state.end_date
        
        # Run the analysis
        with st.spinner("Analyzing correlation between clinical trials and stock price movements..."):
            try:
                # Generate the correlation analysis
                analysis = llm.generate_stock_correlation_analysis(
                    ticker, 
                    trials, 
                    stock_data, 
                    start_date, 
                    end_date
                )
                
                # Store the result
                st.session_state.correlation_analysis = analysis
                st.session_state.analyzed_data = True
                st.session_state.analysis_requested = False
                
                # Force a rerun to display the results without losing state
                st.rerun()
            except Exception as e:
                st.error(f"Error generating analysis: {str(e)}")
                st.session_state.correlation_analysis = f"Error generating analysis: {str(e)}"
                st.session_state.analyzed_data = True
                st.session_state.analysis_requested = False
                
                # Force a rerun here too to ensure consistent behavior
                st.rerun()

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
        
        # Reset correlation analysis if ticker changes
        if ticker != st.session_state.current_ticker:
            clear_analysis()
        
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
    analyze_button = st.button("Analyze Sponsor Focus", use_container_width=True, key="analyze_btn")
    
    # Process when button is clicked
    if analyze_button:
        # Reset analysis state for new search
        clear_analysis()
        
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
                
            # Store data in session state for correlation analysis
            st.session_state.current_ticker = ticker
            st.session_state.current_trials = trials
            st.session_state.start_date = start_date
            st.session_state.end_date = end_date
                
            # Show number of trials
            st.success(f"Found {len(trials)} clinical trials for {sponsor_name} between {start_date} and {end_date}")
            
            # Fetch stock data
            with st.spinner(f"Fetching stock data for {ticker}..."):
                stock_data = get_stock_data(ticker, start_date, end_date)
                # Store stock data in session state
                st.session_state.current_stock_data = stock_data
            
            # Generate analysis with Gemini
            analysis = llm.generate_sponsor_analysis(trials, sponsor_name)
            
            # Display analysis and trial data
            st.markdown("## Research Focus Analysis")
            
            # Create tabs for analysis and raw data
            tab1, tab2, tab3, tab4 = st.tabs(["AI-Generated Analysis", "Trial Data", "Timeline View", "Stock Price Analysis"])
            
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
            
            with tab4:
                st.subheader(f"Stock Price Analysis for {ticker}")
                
                if stock_data is not None and not stock_data.empty:
                    # Create plot
                    plot_buf = plot_stock_with_trials(stock_data, trials, ticker, start_date, end_date)
                    
                    if plot_buf:
                        # Display the plot
                        st.image(plot_buf, use_column_width=True)
                        
                        # Add explanation of the visualization
                        st.markdown("""
                        ### Visualization Details:
                        - **Blue Line:** Stock price (Adjusted Close or Close)
                        - **Red Vertical Lines:** Clinical trial start dates (when a trial officially began)
                        - **Green Vertical Lines:** Analysis period boundaries
                        - **Red Dots:** Stock price value on each trial start date
                        - **Number Labels:** Trial identifiers (NCT ID numbers)
                        
                        The visualization shows how clinical trial events correlate with stock price movements.
                        Each red line represents the exact date when a clinical trial officially started, which can 
                        be a significant event in the company's R&D pipeline. These start dates often coincide with 
                        important company announcements that may affect stock price.
                        """)
                        
                        # Add AI analysis button - use a form to prevent page resets
                        st.markdown("---")
                        
                        # Only show the analysis button if we have both valid stock data and trials with start dates
                        trials_with_dates = [t for t in trials if t.get('start_date')]
                        
                        if trials_with_dates:
                            # If analysis is complete, show results first
                            if st.session_state.analyzed_data:
                                st.markdown("### AI-Generated Stock Price Correlation Analysis")
                                st.markdown(st.session_state.correlation_analysis)
                                
                                # Add citation
                                st.markdown("---")
                                st.caption("Analysis generated by Google Gemini AI based on stock price data and clinical trial events")
                                
                                # Add a button to regenerate the analysis
                                if st.button("Regenerate Analysis", key="regenerate_btn", use_container_width=True):
                                    clear_analysis()
                                    st.session_state.analysis_requested = True
                            elif not st.session_state.analysis_requested:
                                # Create a button to request analysis
                                st.button(
                                    "Generate AI Correlation Analysis", 
                                    on_click=request_analysis,
                                    key="request_analysis_btn",
                                    use_container_width=True,
                                    help="Use AI to analyze the correlation between clinical trial start dates and stock price movements"
                                )
                            else:
                                # If analysis is in progress, just show a message
                                st.info("Analysis in progress... Please wait.")
                        else:
                            st.info("Correlation analysis is not available because no trials in the selected set have start dates that overlap with the stock data period.")
                        
                        # Show stock data table
                        with st.expander("View Stock Price Data"):
                            # For MultiIndex DataFrames, simplify the display
                            if isinstance(stock_data.columns, pd.MultiIndex):
                                # Create a simpler view with just the key columns for the selected ticker
                                display_df = pd.DataFrame({
                                    'Open': stock_data[('Open', ticker)],
                                    'High': stock_data[('High', ticker)],
                                    'Low': stock_data[('Low', ticker)],
                                    'Close': stock_data[('Close', ticker)],
                                    'Volume': stock_data[('Volume', ticker)]
                                })
                                if ('Adj Close', ticker) in stock_data.columns:
                                    display_df['Adj Close'] = stock_data[('Adj Close', ticker)]
                                
                                st.dataframe(display_df, use_container_width=True)
                                
                                # Download option for simplified data
                                csv = display_df.to_csv()
                            else:
                                # Regular dataframe display
                                st.dataframe(stock_data, use_container_width=True)
                                
                                # Download option for original data
                                csv = stock_data.to_csv()
                                
                            st.download_button(
                                label="Download Stock Data as CSV",
                                data=csv,
                                file_name=f"{ticker}_stock_data_{start_date}_to_{end_date}.csv",
                                mime="text/csv",
                            )
                    else:
                        st.error("Error generating the stock price visualization.")
                else:
                    st.warning(f"No stock data available for {ticker} in the selected date range.")
                    st.info("This could be due to an invalid ticker symbol or the selected date range falling on non-trading days.")

    # Check if we need to run analysis (outside of button click)
    if st.session_state.analysis_requested and not st.session_state.analyzed_data:
        perform_correlation_analysis()

# Add explanatory info in sidebar
st.sidebar.title("About this Tool")
st.sidebar.markdown("""
This is a simplified version of the Clinical Trial - Stock Correlation analyzer.

### How it works:
1. Enter a stock ticker symbol for a pharmaceutical company
2. Select a date range to filter clinical trials
3. Click "Analyze" to retrieve clinical trial data
4. AI summarizes the company's research focus
5. View stock price correlation with clinical trials

### Data Sources:
- ClinicalTrials.gov API (for trial data)
- Yahoo Finance (for stock data)
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