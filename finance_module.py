import json
import os
import datetime
import pandas as pd
import yfinance as yf
import streamlit as st
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv
import time

# Add a global cache for stock data
if 'stock_data_cache' not in st.session_state:
    st.session_state.stock_data_cache = {}

# Load company name to ticker mapping
def load_company_to_ticker_mapping() -> Dict[str, str]:
    """
    Load the mapping of company names to stock tickers from JSON file.
    
    Returns:
        Dictionary mapping company names to their stock tickers
    """
    try:
        with open('company_name_to_ticker.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"Error loading company-to-ticker mapping: {e}")
        return {}

# Match a company name to its ticker symbol
def match_company_to_ticker(company_name: str) -> Optional[str]:
    """
    Try to match a company name to its ticker symbol.
    
    Args:
        company_name: The company name to match
        
    Returns:
        The ticker symbol if found, None otherwise
    """
    if not company_name or company_name == 'N/A':
        return None
        
    # Load the mapping dictionary
    company_to_ticker = load_company_to_ticker_mapping()
    
    # Direct match
    if company_name in company_to_ticker:
        return company_to_ticker[company_name]
    
    # Try parts of the name (e.g., "Pfizer Inc" should match "Pfizer")
    words = company_name.split()
    if len(words) > 1:
        for word in words:
            if len(word) > 3 and word in company_to_ticker:  # Avoid matching short words
                return company_to_ticker[word]
    
    # Case insensitive match
    for known_name, ticker in company_to_ticker.items():
        if known_name.lower() in company_name.lower():
            return ticker
    
    return None

# Fetch stock data using yfinance
def fetch_stock_data(ticker: str, days: int = 90) -> Optional[pd.DataFrame]:
    """
    Fetch stock data for a given ticker using yfinance.
    Includes caching mechanism to avoid redundant API calls.
    
    Args:
        ticker: The stock ticker symbol
        days: Number of days of historical data to fetch
        
    Returns:
        DataFrame with stock data or None if the fetch failed
    """
    try:
        # Calculate cache key based on ticker and days
        cache_key = f"{ticker}_{days}"
        
        # Check if data is in cache and not expired (cache valid for 1 hour)
        if cache_key in st.session_state.stock_data_cache:
            cache_entry = st.session_state.stock_data_cache[cache_key]
            cache_time = cache_entry.get('timestamp')
            
            # Cache is valid for 1 hour
            if cache_time and (datetime.datetime.now() - cache_time).seconds < 3600:
                return cache_entry.get('data')
        
        # Calculate start and end dates
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        st.info(f"Fetching data for {ticker} from Yahoo Finance...")
        
        # Create Ticker object (preferred over direct download)
        ticker_obj = yf.Ticker(ticker)
        
        # Try using the history method with start/end dates
        stock_data = ticker_obj.history(start=start_date, end=end_date)
        
        # If empty, try using period parameter instead
        if stock_data.empty:
            # Map days to period parameter
            if days <= 7:
                period = "1wk"
            elif days <= 30:
                period = "1mo"
            elif days <= 90:
                period = "3mo"
            elif days <= 180:
                period = "6mo"
            elif days <= 365:
                period = "1y"
            elif days <= 730:
                period = "2y"
            elif days <= 1825:
                period = "5y"
            else:
                period = "max"
                
            st.info(f"Trying with period={period} instead of exact dates")
            stock_data = ticker_obj.history(period=period)
        
        # Try alternative tickers for specific cases
        if stock_data.empty and ticker in ["AZN", "BMY"]:
            alternative_tickers = {
                "AZN": ["AZN.L", "AZNCF"],
                "BMY": ["BMY.MX", "BMYQF"]
            }
            
            st.info(f"Trying alternative tickers for {ticker}...")
            
            for alt_ticker in alternative_tickers.get(ticker, []):
                try:
                    alt_obj = yf.Ticker(alt_ticker)
                    alt_data = alt_obj.history(start=start_date, end=end_date)
                    if not alt_data.empty:
                        st.success(f"Successfully fetched data using alternative ticker {alt_ticker}")
                        stock_data = alt_data
                        break
                except Exception as e:
                    st.warning(f"Failed with alternative ticker {alt_ticker}: {e}")
                    continue
        
        if stock_data.empty:
            st.warning(f"No stock data available for ticker {ticker} from Yahoo Finance")
            return None
            
        # Calculate additional metrics
        stock_data['Daily Return'] = stock_data['Close'].pct_change() * 100
        stock_data['7-Day MA'] = stock_data['Close'].rolling(window=7).mean()
        stock_data['30-Day MA'] = stock_data['Close'].rolling(window=30).mean()
        
        # Store in cache with timestamp
        st.session_state.stock_data_cache[cache_key] = {
            'data': stock_data,
            'timestamp': datetime.datetime.now()
        }
        
        return stock_data
    except Exception as e:
        st.warning(f"Error fetching stock data for {ticker}: {e}")
        return None

# New function: Batch process multiple tickers to fetch stock data efficiently
def batch_fetch_stock_data(tickers: List[str], days: int = 90) -> Dict[str, pd.DataFrame]:
    """
    Fetch stock data for multiple tickers in batch to minimize API calls and
    improve efficiency, with caching to avoid redundant fetches.
    
    Args:
        tickers: List of stock ticker symbols to fetch
        days: Number of days of historical data to fetch
        
    Returns:
        Dictionary mapping tickers to their stock data DataFrames
    """
    results = {}
    unique_tickers = list(set(tickers))  # Remove duplicates
    
    if not unique_tickers:
        return results
    
    st.info(f"Processing {len(unique_tickers)} unique tickers in batch mode")
    
    progress_bar = st.progress(0)
    
    for batch_idx, ticker in enumerate(unique_tickers):
        # Update progress
        progress = ((batch_idx + 1) / len(unique_tickers))
        progress_bar.progress(progress)
        
        # Fetch data for this ticker
        stock_data = fetch_stock_data(ticker, days)
        if stock_data is not None:
            results[ticker] = stock_data
    
    progress_bar.progress(1.0)
    progress_bar.empty()
    
    return results

# Plot stock data with event marker
def plot_stock_data(stock_data: pd.DataFrame, ticker: str, event_date: Optional[str] = None) -> plt.Figure:
    """
    Create a plot of stock data with an event marker.
    
    Args:
        stock_data: DataFrame with stock data
        ticker: The stock ticker symbol
        event_date: The date of the event to mark (e.g., trial update date)
        
    Returns:
        Matplotlib figure with the plot
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot the close price
    ax.plot(stock_data.index, stock_data['Close'], label='Close Price', color='blue')
    
    # Plot moving averages
    ax.plot(stock_data.index, stock_data['7-Day MA'], label='7-Day MA', color='red', linestyle='--')
    ax.plot(stock_data.index, stock_data['30-Day MA'], label='30-Day MA', color='green', linestyle='-.')
    
    # Add event marker if provided
    if event_date:
        try:
            event_date = datetime.datetime.strptime(event_date, '%Y-%m-%d')
            if event_date in stock_data.index:
                ax.axvline(x=event_date, color='purple', linestyle='--', alpha=0.7)
                ax.text(event_date, stock_data['Close'].max(), 'Trial Update', 
                        rotation=90, color='purple', fontsize=10)
        except:
            # If event date parsing fails, ignore the marker
            pass
    
    # Label axes and add title
    ax.set_xlabel('Date')
    ax.set_ylabel('Price ($)')
    ax.set_title(f'{ticker} Stock Price')
    
    # Add legend
    ax.legend()
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Adjust layout
    plt.tight_layout()
    
    return fig

# Generate market impact summary with LLM
def analyze_market_impact(study_data: Dict, stock_data: pd.DataFrame, ticker: str) -> str:
    """
    Generate a market impact summary using LLM.
    
    Args:
        study_data: Dictionary with clinical trial data
        stock_data: DataFrame with stock data
        ticker: The stock ticker symbol
        
    Returns:
        Summary of potential market impact
    """
    from app import model  # Import Gemini model
    
    # Extract relevant data for analysis
    phase = study_data.get('phase', 'N/A')
    title = study_data.get('brief_title', 'N/A')
    company = study_data.get('sponsor', 'N/A')
    
    # Calculate simple metrics
    if len(stock_data) > 30:
        recent_return = stock_data['Daily Return'].iloc[-30:].mean()
        recent_volatility = stock_data['Daily Return'].iloc[-30:].std()
        price_change_pct = ((stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[-30]) / 
                            stock_data['Close'].iloc[-30]) * 100
    else:
        recent_return = stock_data['Daily Return'].mean()
        recent_volatility = stock_data['Daily Return'].std()
        price_change_pct = ((stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[0]) / 
                            stock_data['Close'].iloc[0]) * 100
    
    # Create a prompt for the LLM
    prompt = f"""
    Analyze the potential market impact of this clinical trial on {company} ({ticker}).
    
    Trial Information:
    - Title: {title}
    - Phase: {phase}
    - Sponsor: {company}
    
    Recent Stock Performance:
    - 30-day Price Change: {price_change_pct:.2f}%
    - Average Daily Return: {recent_return:.2f}%
    - Volatility (StdDev of Returns): {recent_volatility:.2f}%
    
    Based on this information, provide a short analysis (2-3 sentences) of:
    1. The potential market relevance of this trial given its phase and company
    2. How this might affect investor sentiment towards {ticker}
    3. A very brief investment relevance rating (Low/Medium/High)
    
    Your analysis should be concise, focused on the financial aspects rather than scientific details.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Unable to generate market impact analysis: {str(e)}"

# Calculate market reaction metrics
def calculate_market_metrics(stock_data: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate various market reaction metrics from stock data.
    
    Args:
        stock_data: DataFrame with stock data
        
    Returns:
        Dictionary with calculated metrics
    """
    metrics = {}
    
    if stock_data is None or stock_data.empty:
        return {
            'price_change_pct': None,
            'avg_daily_return': None,
            'volatility': None,
            'volume_change_pct': None
        }
    
    try:
        # Price change percentage (last 30 days)
        if len(stock_data) >= 30:
            metrics['price_change_pct'] = ((stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[-30]) / 
                                        stock_data['Close'].iloc[-30]) * 100
        else:
            metrics['price_change_pct'] = ((stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[0]) / 
                                        stock_data['Close'].iloc[0]) * 100
        
        # Average daily return
        metrics['avg_daily_return'] = stock_data['Daily Return'].mean()
        
        # Volatility (standard deviation of returns)
        metrics['volatility'] = stock_data['Daily Return'].std()
        
        # Volume change percentage
        if len(stock_data) >= 30:
            avg_volume_before = stock_data['Volume'].iloc[-30:-15].mean()
            avg_volume_after = stock_data['Volume'].iloc[-15:].mean()
            
            if avg_volume_before > 0:
                metrics['volume_change_pct'] = ((avg_volume_after - avg_volume_before) / 
                                            avg_volume_before) * 100
            else:
                metrics['volume_change_pct'] = 0
        else:
            metrics['volume_change_pct'] = 0
    
    except Exception as e:
        st.warning(f"Error calculating market metrics: {e}")
        return {
            'price_change_pct': None,
            'avg_daily_return': None,
            'volatility': None,
            'volume_change_pct': None
        }
    
    return metrics

# Add financial data to clinical trial studies - OPTIMIZED VERSION
def enrich_studies_with_financial_data(studies: List[Dict]) -> List[Dict]:
    """
    Enrich the clinical trial studies with financial data using batch processing
    for improved efficiency and reduced API calls.
    
    Args:
        studies: List of dictionaries containing study data
        
    Returns:
        List of dictionaries with enriched data
    """
    # First filter to only studies with matching tickers
    filtered_studies = filter_studies_with_tickers(studies)
    
    # Extract unique tickers and determine required fetch period
    tickers_to_fetch = {}
    for study in filtered_studies:
        ticker = study.get('ticker')
        if not ticker:
            continue
            
        # Get trial start date if available to determine fetch period
        start_date_str = study.get('start_date')
        days_to_fetch = 365  # Default to 1 year of data
        
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
        
        # Store the maximum days needed for each ticker
        if ticker in tickers_to_fetch:
            tickers_to_fetch[ticker] = max(tickers_to_fetch[ticker], days_to_fetch)
        else:
            tickers_to_fetch[ticker] = days_to_fetch
    
    # Batch fetch stock data for all unique tickers
    with st.spinner(f"Fetching stock data for {len(tickers_to_fetch)} tickers in batch mode..."):
        # First try to fetch from cache for all tickers
        stock_data_dict = {}
        tickers_to_fetch_live = {}
        
        # Check which tickers need to be fetched from API vs. cache
        for ticker, days in tickers_to_fetch.items():
            cache_key = f"{ticker}_{days}"
            if cache_key in st.session_state.stock_data_cache:
                cache_entry = st.session_state.stock_data_cache[cache_key]
                cache_time = cache_entry.get('timestamp')
                
                # Cache is valid for 1 hour
                if cache_time and (datetime.datetime.now() - cache_time).seconds < 3600:
                    stock_data_dict[ticker] = cache_entry.get('data')
                    continue
            
            # If not in cache or expired, mark for live fetch
            tickers_to_fetch_live[ticker] = days
        
        # Fetch remaining tickers from API
        if tickers_to_fetch_live:
            st.info(f"Fetching {len(tickers_to_fetch_live)} tickers from API (remainder from cache)")
            for ticker, days in tickers_to_fetch_live.items():
                stock_data = fetch_stock_data(ticker, days)
                if stock_data is not None:
                    stock_data_dict[ticker] = stock_data
    
    # Process each study with the fetched stock data
    enriched_studies = []
    for study in filtered_studies:
        enriched_study = study.copy()
        
        # Extract ticker (the ticker was already added by filter_studies_with_tickers)
        ticker = study.get('ticker')
        
        if ticker and ticker in stock_data_dict:
            stock_data = stock_data_dict[ticker]
            
            if stock_data is not None:
                # Calculate market metrics
                metrics = calculate_market_metrics(stock_data)
                
                # Add metrics to study data
                enriched_study['market_metrics'] = metrics
                
                # Analyze the impact of trial phases on stock price
                impact_analysis = analyze_trial_phase_impact(stock_data, study, ticker)
                enriched_study['trial_impact_analysis'] = impact_analysis
                
                # Flag that this study has financial data
                enriched_study['has_financial_data'] = True
                
                # We won't generate the correlation analysis here to save time
                # It will be generated on-demand when user views the trial-stock page
            else:
                enriched_study['has_financial_data'] = False
        else:
            enriched_study['has_financial_data'] = False
        
        enriched_studies.append(enriched_study)
    
    # Add non-matched studies to our results
    for study in studies:
        if study not in filtered_studies:
            study['has_financial_data'] = False
            enriched_studies.append(study)
    
    return enriched_studies

# ARIMA Model for Forecasting
def build_arima_model(stock_data: pd.DataFrame, trial_dates: List[str]) -> Dict:
    """
    Build an ARIMA model for stock forecasting incorporating clinical trial dates.
    
    Args:
        stock_data: DataFrame with historical stock data
        trial_dates: List of important clinical trial dates as date strings
        
    Returns:
        Dictionary with model results and forecast
    """
    try:
        # Import required libraries
        from statsmodels.tsa.arima.model import ARIMA
        from statsmodels.tsa.stattools import adfuller
        import warnings
        warnings.filterwarnings("ignore")
        
        # Prepare data
        price_series = stock_data['Close'].copy()
        
        # Check stationarity using ADF test
        adf_result = adfuller(price_series.diff().dropna())
        is_stationary = adf_result[1] < 0.05
        
        # Determine parameters
        p, d, q = (0, 1, 0)  # Simple default
        if not is_stationary:
            d = 1  # First difference if not stationary
        
        # Create and fit ARIMA model
        model = ARIMA(price_series, order=(p, d, q))
        model_fit = model.fit()
        
        # Create forecasts for next 30 days
        forecast = model_fit.forecast(steps=30)
        
        # Calculate prediction intervals
        pred_intervals = model_fit.get_forecast(steps=30).conf_int()
        
        # Create prediction DataFrame
        predictions = pd.DataFrame({
            'forecast': forecast,
            'lower_ci': pred_intervals.iloc[:, 0],
            'upper_ci': pred_intervals.iloc[:, 1]
        })
        
        # Check if stock_data index is timezone-aware
        is_tz_aware = stock_data.index.tzinfo is not None
        
        # Add trial dates to the model results for visualization later
        formatted_trial_dates = []
        for date_str in trial_dates:
            if date_str:
                try:
                    # Handle different date formats
                    for fmt in ['%B %Y', '%Y-%m-%d', '%b %d, %Y']:
                        try:
                            date_obj = datetime.datetime.strptime(date_str, fmt)
                            # Convert to pandas Timestamp
                            date_obj = pd.Timestamp(date_obj)
                            
                            # Handle timezone issues
                            if is_tz_aware and date_obj.tzinfo is None:
                                # If stock data is tz-aware but date is naive, 
                                # localize date to the same timezone as stock_data
                                stock_tz = stock_data.index[0].tzinfo
                                date_obj = date_obj.tz_localize(stock_tz)
                            elif not is_tz_aware and date_obj.tzinfo is not None:
                                # If stock data is naive but date is tz-aware,
                                # make the date naive
                                date_obj = date_obj.tz_localize(None)
                                
                            formatted_trial_dates.append(date_obj)
                            break
                        except:
                            continue
                except Exception as e:
                    st.warning(f"Could not parse date: {date_str}, error: {e}")
                
        return {
            'model': model_fit,
            'forecast': predictions,
            'trial_dates': formatted_trial_dates,
            'p': p,
            'd': d,
            'q': q,
            'is_stationary': is_stationary,
            'adf_pvalue': adf_result[1]
        }
        
    except Exception as e:
        st.warning(f"Error building ARIMA model: {e}")
        return None

def plot_stock_forecast(ticker: str, stock_data: pd.DataFrame, 
                       forecast_data: Dict, trial_data: Dict) -> plt.Figure:
    """
    Create stock forecast visualization with trial events marked.
    
    Args:
        ticker: The stock ticker symbol
        stock_data: DataFrame with historical stock data
        forecast_data: Dictionary with forecast results from ARIMA model
        trial_data: Dictionary with trial information including dates
        
    Returns:
        Matplotlib figure with the plot
    """
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Plot historical data
    ax.plot(stock_data.index, stock_data['Close'], label='Historical Prices', color='blue')
    
    # Get forecast data
    forecast = forecast_data['forecast']
    forecast_dates = pd.date_range(start=stock_data.index[-1], periods=len(forecast)+1)[1:]
    
    # Plot forecast
    ax.plot(forecast_dates, forecast['forecast'], label='ARIMA Forecast', color='red', linestyle='--')
    ax.fill_between(forecast_dates, forecast['lower_ci'], forecast['upper_ci'], 
                   color='red', alpha=0.2, label='95% Confidence Interval')
    
    # Check if stock_data index is timezone-aware
    is_tz_aware = stock_data.index.tzinfo is not None
    
    # Add trial dates as vertical lines
    colors = ['purple', 'green', 'orange', 'magenta']
    trial_events = {
        'start_date': 'Trial Start',
        'primary_completion_date': 'Primary Completion',
        'completion_date': 'Completion',
        'last_update_date': 'Last Update'
    }
    
    for i, (event_type, label) in enumerate(trial_events.items()):
        if event_type in trial_data and trial_data[event_type]:
            try:
                # Parse date using flexible parsing
                date_str = trial_data[event_type]
                for fmt in ['%B %Y', '%Y-%m-%d', '%b %d, %Y']:
                    try:
                        event_date = datetime.datetime.strptime(date_str, fmt)
                        
                        # Convert to pandas Timestamp and handle timezone
                        event_date = pd.Timestamp(event_date)
                        
                        # Handle timezone issues
                        if is_tz_aware and event_date.tzinfo is None:
                            # If stock data is tz-aware but event date is naive, 
                            # localize event_date to the same timezone as stock_data
                            stock_tz = stock_data.index[0].tzinfo
                            event_date = event_date.tz_localize(stock_tz)
                        elif not is_tz_aware and event_date.tzinfo is not None:
                            # If stock data is naive but event date is tz-aware,
                            # make the event_date naive
                            event_date = event_date.tz_localize(None)
                        
                        # Only show if within our graph timeframe
                        if (event_date >= stock_data.index[0] and 
                            (event_date <= stock_data.index[-1] or event_date <= forecast_dates[-1])):
                            ax.axvline(x=event_date, color=colors[i % len(colors)], 
                                      linestyle=':', alpha=0.7)
                            y_pos = stock_data['Close'].min() + (i * (stock_data['Close'].max() - stock_data['Close'].min()) * 0.05)
                            ax.text(event_date, y_pos, f"{label}",
                                   rotation=90, color=colors[i % len(colors)], fontsize=10)
                        break
                    except:
                        continue
            except Exception as e:
                st.warning(f"Error plotting event date: {e}")
                
    # Label axes and add title
    ax.set_xlabel('Date')
    ax.set_ylabel('Price ($)')
    ax.set_title(f'{ticker} Stock Price & Forecast with Trial Events')
    ax.legend(loc='upper left')
    
    # Format x-axis dates
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

def analyze_forecast_impact(study_data: Dict, stock_data: pd.DataFrame, 
                          forecast_data: Dict, ticker: str) -> str:
    """
    Generate LLM commentary on forecast and trial impact.
    
    Args:
        study_data: Dictionary with clinical trial data
        stock_data: DataFrame with stock data
        forecast_data: Dictionary with ARIMA model results
        ticker: The stock ticker symbol
        
    Returns:
        Summary of potential market impact based on forecast
    """
    from app import model  # Import Gemini model
    
    # Extract relevant data 
    phase = study_data.get('phase', 'N/A')
    title = study_data.get('brief_title', 'N/A')
    status = study_data.get('status', 'N/A')
    start_date = study_data.get('start_date', 'N/A')
    
    # Calculate change metrics
    forecast = forecast_data['forecast']
    current_price = stock_data['Close'].iloc[-1]
    predicted_end_price = forecast['forecast'].iloc[-1]
    predicted_change_pct = ((predicted_end_price - current_price) / current_price) * 100
    
    # Create prompt for LLM
    prompt = f"""
    Analyze the forecasted stock price movement for {ticker} in relation to their clinical trial:
    
    Trial Information:
    - Title: {title}
    - Phase: {phase}
    - Status: {status}
    - Start Date: {start_date}
    
    Current Stock Information:
    - Current Price: ${current_price:.2f}
    - Forecasted Price (30 days): ${predicted_end_price:.2f}
    - Projected Change: {predicted_change_pct:.2f}%
    
    Based on this information, provide a brief analysis (3-4 sentences) of:
    1. How the clinical trial timeline might influence stock movement
    2. What investors should watch for regarding this trial
    3. How this forecast aligns with typical market reactions to {phase} trials
    4. What investment strategy might be appropriate given this trial-stock correlation pattern
    
    Your analysis should focus on the relationship between clinical milestones and potential market impact.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Unable to generate forecast analysis: {str(e)}"

# Filter studies to only include those with a matching ticker
def filter_studies_with_tickers(studies: List[Dict]) -> List[Dict]:
    """
    Filter studies to only include those where the sponsor company has a matching ticker.
    Uses batch processing for better performance.
    
    Args:
        studies: List of dictionaries containing study data
        
    Returns:
        List of dictionaries with only studies that have matching tickers
    """
    if not studies:
        return []
        
    # Extract all unique sponsors to process in batch
    sponsors = {}
    for i, study in enumerate(studies):
        sponsor = study.get('sponsor', 'N/A')
        if sponsor != 'N/A':
            sponsors[sponsor] = sponsors.get(sponsor, []) + [i]
    
    st.info(f"Matching {len(sponsors)} unique sponsors to tickers")
    
    # Process sponsor-to-ticker mapping in batch
    sponsor_ticker_map = {}
    for sponsor in sponsors.keys():
        ticker = match_company_to_ticker(sponsor)
        if ticker:
            sponsor_ticker_map[sponsor] = ticker
    
    # Now apply the tickers to studies
    filtered_studies = []
    matched_count = 0
    total_studies = len(studies)
    
    for i, study in enumerate(studies):
        sponsor = study.get('sponsor', 'N/A')
        if sponsor in sponsor_ticker_map:
            # Add ticker to the study
            study['ticker'] = sponsor_ticker_map[sponsor]
            filtered_studies.append(study)
            matched_count += 1
    
    match_percentage = (matched_count / total_studies * 100) if total_studies > 0 else 0
    st.info(f"Found ticker matches for {matched_count} out of {total_studies} studies ({match_percentage:.1f}%)")
    
    return filtered_studies

# Analyze stock price changes around clinical trial events
def analyze_trial_phase_impact(stock_data: pd.DataFrame, trial_data: Dict, ticker: str) -> Dict:
    """
    Analyze stock price changes around clinical trial phases and key dates.
    
    Args:
        stock_data: DataFrame with historical stock data
        trial_data: Dictionary with trial information including dates
        ticker: The stock ticker symbol
        
    Returns:
        Dictionary with analysis results for each trial phase/event
    """
    if stock_data is None or stock_data.empty:
        return {"error": "No stock data available for analysis"}
    
    results = {}
    
    # Key trial events to analyze
    trial_events = {
        'start_date': 'Trial Start',
        'primary_completion_date': 'Primary Completion',
        'completion_date': 'Trial Completion',
        'results_first_posted_date': 'Results Posted',
        'last_update_date': 'Last Update'
    }
    
    # Analysis windows (days before and after event)
    windows = [
        (5, 5),   # Short-term: 5 days before and after
        (10, 10), # Medium-term: 10 days before and after
        (30, 30)  # Long-term: 30 days before and after
    ]
    
    # Check if stock_data index is timezone-aware
    is_tz_aware = stock_data.index.tzinfo is not None
    
    for event_key, event_name in trial_events.items():
        if event_key in trial_data and trial_data[event_key]:
            date_str = trial_data[event_key]
            event_date = None
            
            # Try to parse the date with different formats
            for fmt in ['%Y-%m-%d', '%B %Y', '%b %d, %Y']:
                try:
                    event_date = datetime.datetime.strptime(date_str, fmt)
                    break
                except:
                    continue
            
            if event_date:
                # Convert to pandas Timestamp
                event_date = pd.Timestamp(event_date)
                
                # Handle timezone issues - make both timezone-aware or both naive
                if is_tz_aware and event_date.tzinfo is None:
                    # If stock data is tz-aware but event date is naive, 
                    # localize event_date to the same timezone as stock_data
                    stock_tz = stock_data.index[0].tzinfo
                    event_date = event_date.tz_localize(stock_tz)
                elif not is_tz_aware and event_date.tzinfo is not None:
                    # If stock data is naive but event date is tz-aware,
                    # make the event_date naive
                    event_date = event_date.tz_localize(None)
                
                # For each analysis window
                window_results = {}
                for days_before, days_after in windows:
                    # Calculate window boundaries
                    start_date = event_date - pd.Timedelta(days=days_before)
                    end_date = event_date + pd.Timedelta(days=days_after)
                    
                    # Get stock data in window
                    window_data = stock_data[(stock_data.index >= start_date) & 
                                            (stock_data.index <= end_date)]
                    
                    if not window_data.empty and len(window_data) > 1:
                        # Calculate metrics
                        price_change = ((window_data['Close'].iloc[-1] - window_data['Close'].iloc[0]) / 
                                       window_data['Close'].iloc[0]) * 100
                        
                        # Calculate pre-event and post-event returns
                        pre_event_data = window_data[window_data.index < event_date]
                        post_event_data = window_data[window_data.index >= event_date]
                        
                        pre_event_change = 0
                        post_event_change = 0
                        
                        if len(pre_event_data) > 1:
                            pre_event_change = ((pre_event_data['Close'].iloc[-1] - pre_event_data['Close'].iloc[0]) / 
                                              pre_event_data['Close'].iloc[0]) * 100
                        
                        if len(post_event_data) > 1:
                            post_event_change = ((post_event_data['Close'].iloc[-1] - post_event_data['Close'].iloc[0]) / 
                                               post_event_data['Close'].iloc[0]) * 100
                        
                        # Calculate volume change
                        avg_vol_before = pre_event_data['Volume'].mean() if not pre_event_data.empty else 0
                        avg_vol_after = post_event_data['Volume'].mean() if not post_event_data.empty else 0
                        
                        vol_change_pct = 0
                        if avg_vol_before > 0 and avg_vol_after > 0:
                            vol_change_pct = ((avg_vol_after - avg_vol_before) / avg_vol_before) * 100
                        
                        # Save window results
                        window_size = f"{days_before}d_before_{days_after}d_after"
                        window_results[window_size] = {
                            'window_price_change_pct': price_change,
                            'pre_event_change_pct': pre_event_change,
                            'post_event_change_pct': post_event_change,
                            'volume_change_pct': vol_change_pct,
                            'price_at_event': window_data.loc[window_data.index >= event_date, 'Close'].iloc[0] if not post_event_data.empty else None,
                            'avg_daily_return': window_data['Daily Return'].mean(),
                            'volatility': window_data['Daily Return'].std()
                        }
                
                results[event_name] = {
                    'date': date_str,
                    'windows': window_results
                }
    
    # Add trial phase specific analysis
    phase = trial_data.get('phase', 'N/A')
    results['phase'] = phase
    
    # Add overall trial sentiment analysis
    sentiment = "Neutral"
    avg_post_event_changes = []
    
    for event in results.values():
        if isinstance(event, dict) and 'windows' in event:
            for window_data in event['windows'].values():
                if window_data['post_event_change_pct'] > 0:
                    avg_post_event_changes.append(window_data['post_event_change_pct'])
    
    if avg_post_event_changes:
        avg_impact = sum(avg_post_event_changes) / len(avg_post_event_changes)
        if avg_impact > 5:
            sentiment = "Very Positive"
        elif avg_impact > 1:
            sentiment = "Positive"
        elif avg_impact < -5:
            sentiment = "Very Negative"
        elif avg_impact < -1:
            sentiment = "Negative"
    
    results['market_sentiment'] = sentiment
    
    return results

# Plot stock data with trial phase markers
def plot_trial_phase_stock_analysis(stock_data: pd.DataFrame, trial_data: Dict, ticker: str) -> plt.Figure:
    """
    Create a detailed visualization that shows stock price movements with clear trial phase markers.
    
    Args:
        stock_data: DataFrame with historical stock data
        trial_data: Dictionary with trial information including dates
        ticker: The stock ticker symbol
        
    Returns:
        Matplotlib figure with the plot
    """
    # Check if we have stock data
    if stock_data is None or stock_data.empty:
        st.warning(f"No stock data available for ticker {ticker}")
        return None
    
    # Create figure with two subplots - price and volume
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    
    # Plot closing price on upper subplot
    ax1.plot(stock_data.index, stock_data['Close'], label='Close Price', color='blue', linewidth=1.5)
    
    # Plot moving averages
    ax1.plot(stock_data.index, stock_data['7-Day MA'], label='7-Day MA', color='red', linestyle='--', alpha=0.7)
    ax1.plot(stock_data.index, stock_data['30-Day MA'], label='30-Day MA', color='green', linestyle='-.', alpha=0.7)
    
    # Plot volume on lower subplot
    ax2.bar(stock_data.index, stock_data['Volume'], color='gray', alpha=0.6, label='Volume')
    
    # Mark key trial events with vertical lines and annotations
    trial_events = {
        'start_date': {'label': 'Trial Start', 'color': 'purple', 'linestyle': '-'},
        'primary_completion_date': {'label': 'Primary Completion', 'color': 'green', 'linestyle': '--'},
        'completion_date': {'label': 'Trial Completion', 'color': 'orange', 'linestyle': '-.'}, 
        'results_first_posted_date': {'label': 'Results Posted', 'color': 'red', 'linestyle': ':'},
        'last_update_date': {'label': 'Last Update', 'color': 'blue', 'linestyle': ':'}
    }
    
    # Phase information
    phase = trial_data.get('phase', 'Unknown')
    status = trial_data.get('overall_status', 'Unknown')
    
    # Add title with phase information
    title = f"{ticker} Stock Price with {phase} Trial Events\nStatus: {status}"
    ax1.set_title(title, fontsize=14)
    
    # Keep track of event dates we've already plotted to avoid duplicates
    plotted_dates = set()
    
    # Check if stock_data index is timezone-aware
    is_tz_aware = stock_data.index.tzinfo is not None
    
    # Plot vertical lines for each event
    for event_key, event_info in trial_events.items():
        if event_key in trial_data and trial_data[event_key]:
            date_str = trial_data[event_key]
            event_date = None
            
            # Try to parse the date with different formats
            for fmt in ['%Y-%m-%d', '%B %Y', '%b %d, %Y']:
                try:
                    event_date = datetime.datetime.strptime(date_str, fmt)
                    break
                except:
                    continue
            
            if event_date and event_date not in plotted_dates:
                # Convert to pandas Timestamp
                event_date = pd.Timestamp(event_date)
                
                # Handle timezone issues
                if is_tz_aware and event_date.tzinfo is None:
                    # If stock data is tz-aware but event date is naive, 
                    # localize event_date to the same timezone as stock_data
                    stock_tz = stock_data.index[0].tzinfo
                    event_date = event_date.tz_localize(stock_tz)
                elif not is_tz_aware and event_date.tzinfo is not None:
                    # If stock data is naive but event date is tz-aware,
                    # make the event_date naive
                    event_date = event_date.tz_localize(None)
                
                # Only plot if the event date is within our stock data range
                if stock_data.index[0] <= pd.Timestamp(event_date) <= stock_data.index[-1]:
                    # Add event to both price and volume plots
                    for ax in [ax1, ax2]:
                        ax.axvline(x=event_date, color=event_info['color'], 
                                  linestyle=event_info['linestyle'], alpha=0.7)
                    
                    # Add text label - position based on subplot
                    label_height = stock_data['Close'].max() * 0.95
                    ax1.text(event_date, label_height, event_info['label'], 
                            rotation=90, color=event_info['color'], fontsize=10, 
                            ha='right', va='top')
                    
                    # Add to plotted dates
                    plotted_dates.add(event_date)
    
    # Analysis results from stock price around trial phases
    impact_analysis = analyze_trial_phase_impact(stock_data, trial_data, ticker)
    
    # Add annotations for significant price changes after events
    annotations = []
    for event_name, event_data in impact_analysis.items():
        if isinstance(event_data, dict) and 'windows' in event_data:
            for window_size, metrics in event_data['windows'].items():
                # Only annotate medium-term significant changes
                if window_size == '10d_before_10d_after' and abs(metrics['post_event_change_pct']) > 5:
                    change = metrics['post_event_change_pct']
                    change_str = f"{event_name}: {change:.1f}% change"
                    annotations.append((event_name, change_str, change))
    
    # Add a text box with key insights
    if annotations:
        insights_text = "\n".join([f"{annot[1]}" for annot in annotations])
        insights_text = f"Key Price Changes:\n{insights_text}"
        
        # Add market sentiment
        sentiment = impact_analysis.get('market_sentiment', 'Neutral')
        insights_text += f"\n\nOverall Market Sentiment: {sentiment}"
        
        # Position the text box in the upper left
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.4)
        ax1.text(0.02, 0.98, insights_text, transform=ax1.transAxes, fontsize=10,
                verticalalignment='top', bbox=props)
    
    # Format axes
    ax1.set_ylabel('Price ($)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Volume', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # Format x-axis date ticks
    plt.xticks(rotation=45)
    fig.tight_layout()
    
    return fig

# Generate comprehensive analysis of trial phase impact on stock price
def generate_trial_stock_correlation_analysis(study_data: Dict, stock_data: pd.DataFrame, 
                                            impact_analysis: Dict, ticker: str) -> str:
    """
    Generate a comprehensive analysis of the relationship between clinical trial phases and stock price.
    
    Args:
        study_data: Dictionary with clinical trial data
        stock_data: DataFrame with stock data
        impact_analysis: Results from the analyze_trial_phase_impact function
        ticker: The stock ticker symbol
        
    Returns:
        Detailed analysis text
    """
    from app import model  # Import Gemini model
    
    # Check if we have the necessary data
    if stock_data is None or stock_data.empty:
        return "Insufficient stock data for analysis."
        
    if impact_analysis is None or "error" in impact_analysis:
        return f"Unable to analyze trial impact: {impact_analysis.get('error', 'Unknown error')}"
    
    # Extract key study information
    study_title = study_data.get('brief_title', 'N/A')
    sponsor = study_data.get('sponsor', 'N/A')
    phase = study_data.get('phase', 'N/A')
    status = study_data.get('overall_status', 'N/A')
    conditions = study_data.get('condition', 'N/A')
    if isinstance(conditions, list):
        conditions = ", ".join(conditions)
    
    # Compile event impact data
    events_data = []
    for event_name, event_data in impact_analysis.items():
        if isinstance(event_data, dict) and 'windows' in event_data:
            for window_size, metrics in event_data['windows'].items():
                if window_size == '10d_before_10d_after':  # Use medium-term window for analysis
                    events_data.append({
                        'event': event_name,
                        'date': event_data.get('date', 'N/A'),
                        'price_change_pct': metrics['window_price_change_pct'],
                        'pre_event_change_pct': metrics['pre_event_change_pct'],
                        'post_event_change_pct': metrics['post_event_change_pct'],
                        'volume_change_pct': metrics['volume_change_pct']
                    })
    
    # Calculate overall stock performance metrics
    overall_change = ((stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[0]) / 
                     stock_data['Close'].iloc[0]) * 100
    
    avg_daily_return = stock_data['Daily Return'].mean()
    volatility = stock_data['Daily Return'].std()
    
    # Create a prompt for the LLM
    prompt = f"""
    Analyze the correlation between clinical trial phases/events and stock price performance for {sponsor} ({ticker}).
    
    TRIAL INFORMATION:
    - Title: {study_title}
    - Phase: {phase}
    - Status: {status}
    - Condition(s): {conditions}
    
    OVERALL STOCK PERFORMANCE:
    - Total Price Change: {overall_change:.2f}%
    - Average Daily Return: {avg_daily_return:.2f}%
    - Volatility: {volatility:.2f}%
    
    TRIAL EVENT IMPACT (10 days before/after each event):
    """
    
    # Add each event's impact data
    for event in events_data:
        prompt += f"""
    {event['event']} ({event['date']}):
    - Overall Window Change: {event['price_change_pct']:.2f}%
    - Pre-event Change: {event['pre_event_change_pct']:.2f}%
    - Post-event Change: {event['post_event_change_pct']:.2f}%
    - Volume Change: {event['volume_change_pct']:.2f}%
        """
    
    # Market sentiment
    sentiment = impact_analysis.get('market_sentiment', 'Neutral')
    prompt += f"\nOverall Market Sentiment: {sentiment}\n"
    
    # Instructions for the analysis
    prompt += """
    Based on this information, please provide a detailed analysis addressing:
    1. How each clinical trial phase/event appears to have impacted the stock price
    2. Which events had the most significant market impact and why
    3. Whether the market reaction aligns with typical patterns for this trial phase
    4. What investment strategy might be appropriate given this trial-stock correlation pattern
    5. Key factors investors should monitor in future trial updates
    
    Your analysis should focus specifically on the relationship between trial events and stock performance.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating analysis: {str(e)}"

# New function for analyzing trial impact with optional sector comparison
def analyze_trial_impact(ticker: str, event_date: datetime.datetime, window: int = 10, compare_sector: bool = False) -> Dict:
    """
    Analyze stock price impact around a specific clinical trial event date.
    
    Args:
        ticker: The stock ticker symbol
        event_date: The date of the clinical trial event
        window: Number of days before and after the event to analyze
        compare_sector: Whether to compare with biotech sector index (IBB)
        
    Returns:
        Dictionary with analysis results and chart data
    """
    try:
        # Convert event_date to pandas Timestamp for comparison
        event_date = pd.Timestamp(event_date)
        
        # Calculate window boundaries
        start_date = event_date - pd.Timedelta(days=window)
        end_date = event_date + pd.Timedelta(days=window)
        
        # Calculate actual days needed based on window, with buffer for weekends/holidays
        days_to_fetch = window * 3  # Fetch extra days to account for weekends/holidays
        
        # Fetch stock data
        stock_data = fetch_stock_data(ticker, days=days_to_fetch)
        
        if stock_data is None or stock_data.empty:
            return {"error": f"No stock data available for {ticker}"}
        
        # Check if stock_data index is timezone-aware
        is_tz_aware = stock_data.index.tzinfo is not None
        
        # Handle timezone issues
        if is_tz_aware and event_date.tzinfo is None:
            # If stock data is tz-aware but event date is naive, 
            # localize event_date to the same timezone as stock_data
            stock_tz = stock_data.index[0].tzinfo
            event_date = event_date.tz_localize(stock_tz)
            start_date = start_date.tz_localize(stock_tz)
            end_date = end_date.tz_localize(stock_tz)
        elif not is_tz_aware and event_date.tzinfo is not None:
            # If stock data is naive but event date is tz-aware,
            # make the event_date naive
            event_date = event_date.tz_localize(None)
            start_date = start_date.tz_localize(None)
            end_date = end_date.tz_localize(None)
        
        # Filter for the window period
        window_data = stock_data[(stock_data.index >= start_date) & (stock_data.index <= end_date)]
        
        if window_data.empty:
            return {"error": f"No stock data available within the window period for {ticker}"}
        
        # Split into pre-event and post-event
        pre_event_data = window_data[window_data.index < event_date]
        event_day_data = window_data[window_data.index == event_date]
        post_event_data = window_data[window_data.index > event_date]
        
        # Check if we have sufficient data
        if len(pre_event_data) == 0 or len(post_event_data) == 0:
            return {"error": "Insufficient data around the event date"}
        
        # Calculate price metrics
        price_at_start = pre_event_data['Close'].iloc[0] if not pre_event_data.empty else None
        price_at_event = event_day_data['Close'].iloc[0] if not event_day_data.empty else post_event_data['Close'].iloc[0]
        price_at_end = post_event_data['Close'].iloc[-1] if not post_event_data.empty else None
        
        # Calculate price changes
        pre_event_change = ((price_at_event - price_at_start) / price_at_start * 100) if price_at_start else None
        post_event_change = ((price_at_end - price_at_event) / price_at_event * 100) if price_at_event and price_at_end else None
        total_change = ((price_at_end - price_at_start) / price_at_start * 100) if price_at_start and price_at_end else None
        
        # Volume metrics
        avg_vol_before = pre_event_data['Volume'].mean() if not pre_event_data.empty else 0
        avg_vol_after = post_event_data['Volume'].mean() if not post_event_data.empty else 0
        vol_change_pct = ((avg_vol_after - avg_vol_before) / avg_vol_before * 100) if avg_vol_before > 0 else 0
        
        # Volatility metrics
        volatility_before = pre_event_data['Daily Return'].std() if len(pre_event_data) > 1 else 0
        volatility_after = post_event_data['Daily Return'].std() if len(post_event_data) > 1 else 0
        volatility_change = ((volatility_after - volatility_before) / volatility_before * 100) if volatility_before > 0 else 0
        
        # Sector comparison if requested
        sector_data = None
        sector_metrics = None
        if compare_sector:
            sector_ticker = "IBB"  # iShares Nasdaq Biotechnology ETF
            sector_data = fetch_stock_data(sector_ticker, days=days_to_fetch)
            
            if sector_data is not None and not sector_data.empty:
                # Check if sector_data timezone needs adjustment
                sector_tz_aware = sector_data.index.tzinfo is not None
                if sector_tz_aware != is_tz_aware:
                    # Make timezone handling consistent
                    if sector_tz_aware and not is_tz_aware:
                        # Make sector data timezone-naive to match stock data
                        sector_data.index = sector_data.index.tz_localize(None)
                    elif not sector_tz_aware and is_tz_aware:
                        # Make sector data timezone-aware to match stock data
                        stock_tz = stock_data.index[0].tzinfo
                        sector_data.index = sector_data.index.tz_localize(stock_tz)
                
                # Filter for the window period
                sector_window = sector_data[(sector_data.index >= start_date) & (sector_data.index <= end_date)]
                
                if not sector_window.empty:
                    # Split sector data
                    sector_pre = sector_window[sector_window.index < event_date]
                    sector_event = sector_window[sector_window.index == event_date]
                    sector_post = sector_window[sector_window.index > event_date]
                    
                    if len(sector_pre) > 0 and len(sector_post) > 0:
                        # Calculate sector price metrics
                        sector_price_start = sector_pre['Close'].iloc[0]
                        sector_price_event = sector_event['Close'].iloc[0] if not sector_event.empty else sector_post['Close'].iloc[0]
                        sector_price_end = sector_post['Close'].iloc[-1]
                        
                        # Calculate sector price changes
                        sector_pre_change = ((sector_price_event - sector_price_start) / sector_price_start * 100)
                        sector_post_change = ((sector_price_end - sector_price_event) / sector_price_event * 100)
                        sector_total_change = ((sector_price_end - sector_price_start) / sector_price_start * 100)
                        
                        # Calculate relative performance (stock vs sector)
                        relative_pre = pre_event_change - sector_pre_change if pre_event_change is not None else None
                        relative_post = post_event_change - sector_post_change if post_event_change is not None else None
                        relative_total = total_change - sector_total_change if total_change is not None else None
                        
                        sector_metrics = {
                            'ticker': sector_ticker,
                            'pre_event_change': sector_pre_change,
                            'post_event_change': sector_post_change,
                            'total_change': sector_total_change,
                            'relative_pre': relative_pre,
                            'relative_post': relative_post,
                            'relative_total': relative_total
                        }
        
        # Create result dictionary
        result = {
            'ticker': ticker,
            'event_date': event_date,
            'window': window,
            'price_metrics': {
                'price_at_start': price_at_start,
                'price_at_event': price_at_event,
                'price_at_end': price_at_end,
                'pre_event_change': pre_event_change,
                'post_event_change': post_event_change,
                'total_change': total_change
            },
            'volume_metrics': {
                'avg_vol_before': avg_vol_before,
                'avg_vol_after': avg_vol_after,
                'vol_change_pct': vol_change_pct
            },
            'volatility_metrics': {
                'volatility_before': volatility_before,
                'volatility_after': volatility_after,
                'volatility_change': volatility_change
            },
            'stock_data': window_data,
            'sector_comparison': sector_metrics,
            'sector_data': sector_window if compare_sector and 'sector_window' in locals() else None
        }
        
        return result
    
    except Exception as e:
        return {"error": f"Error analyzing trial impact: {str(e)}"}

# Function to create a visualization of the trial event impact
def plot_trial_impact(impact_result: Dict) -> plt.Figure:
    """
    Create a visualization of stock price impact around a clinical trial event.
    
    Args:
        impact_result: Dictionary with trial impact analysis results
        
    Returns:
        Matplotlib figure with the visualization
    """
    if "error" in impact_result:
        return None
    
    # Extract data from the impact result
    ticker = impact_result['ticker']
    event_date = impact_result['event_date']
    window = impact_result['window']
    stock_data = impact_result['stock_data']
    sector_data = impact_result.get('sector_data')
    sector_comparison = impact_result.get('sector_comparison')
    
    # Determine if we're including sector comparison
    include_sector = sector_data is not None and sector_comparison is not None
    
    # Create figure with subplots - price and volume
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    
    # Plot stock price on upper subplot
    ax1.plot(stock_data.index, stock_data['Close'], label=f'{ticker} Close', color='blue', linewidth=1.5)
    
    # Plot moving averages
    ax1.plot(stock_data.index, stock_data['7-Day MA'], label='7-Day MA', color='red', linestyle='--', alpha=0.7)
    
    # Add sector comparison if available
    if include_sector:
        # Normalize sector data for comparison (set both to 100 at start)
        first_stock_price = stock_data['Close'].iloc[0]
        first_sector_price = sector_data['Close'].iloc[0]
        
        normalized_stock = stock_data['Close'] / first_stock_price * 100
        normalized_sector = sector_data['Close'] / first_sector_price * 100
        
        # Plot normalized data
        ax1.plot(normalized_stock.index, normalized_stock, label=f'{ticker} (normalized)', color='blue', linewidth=1.5)
        ax1.plot(normalized_sector.index, normalized_sector, label=f'{sector_comparison["ticker"]} (normalized)', color='green', linewidth=1.5)
    
    # Add event line
    ax1.axvline(x=event_date, color='purple', linestyle='-', alpha=0.7)
    ax1.text(event_date, stock_data['Close'].max(), 'Event', rotation=90, color='purple', fontsize=12, ha='right')
    
    # Plot volume on lower subplot
    ax2.bar(stock_data.index, stock_data['Volume'], color='gray', alpha=0.6, label='Volume')
    ax2.axvline(x=event_date, color='purple', linestyle='-', alpha=0.7)
    
    # Add annotations for price changes
    price_metrics = impact_result['price_metrics']
    pre_change = price_metrics.get('pre_event_change')
    post_change = price_metrics.get('post_event_change')
    total_change = price_metrics.get('total_change')
    
    # Prepare annotation text
    annotation_text = f"Pre-Event: {pre_change:.2f}%\nPost-Event: {post_change:.2f}%\nTotal: {total_change:.2f}%"
    
    # Add sector comparison annotation if available
    if sector_comparison:
        annotation_text += f"\n\nSector ({sector_comparison['ticker']}):\nPre: {sector_comparison['pre_event_change']:.2f}%\nPost: {sector_comparison['post_event_change']:.2f}%\n"
        annotation_text += f"Relative Performance:\nPre: {sector_comparison['relative_pre']:.2f}%\nPost: {sector_comparison['relative_post']:.2f}%"
    
    # Add text box with metrics
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.4)
    ax1.text(0.02, 0.98, annotation_text, transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', bbox=props)
    
    # Add title
    title = f"Impact of Clinical Trial Event on {ticker} Stock (±{window} days)"
    if include_sector:
        title += f" vs. {sector_comparison['ticker']} Sector"
    ax1.set_title(title, fontsize=14)
    
    # Format axes
    ax1.set_ylabel('Price ($)' if not include_sector else 'Normalized Price (%)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('Volume', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # Format x-axis date ticks
    plt.xticks(rotation=45)
    fig.tight_layout()
    
    return fig

# Function to get LLM sentiment about trial event impact
def analyze_trial_event_sentiment(ticker: str, impact_result: Dict, trial_data: Dict) -> str:
    """
    Generate an LLM analysis of investor sentiment based on stock reaction to trial event.
    
    Args:
        ticker: The stock ticker symbol
        impact_result: Dictionary with trial impact analysis results
        trial_data: Dictionary with clinical trial information
        
    Returns:
        String with LLM analysis of investor sentiment
    """
    from app import model  # Import Gemini model
    
    if "error" in impact_result:
        return f"Unable to analyze sentiment: {impact_result['error']}"
    
    # Extract data for the prompt
    event_date = impact_result['event_date']
    price_metrics = impact_result['price_metrics']
    volume_metrics = impact_result['volume_metrics']
    volatility_metrics = impact_result['volatility_metrics']
    sector_comparison = impact_result.get('sector_comparison')
    
    # Extract relevant trial data
    phase = trial_data.get('phase', 'N/A')
    title = trial_data.get('brief_title', 'N/A')
    status = trial_data.get('status', 'N/A')
    event_type = trial_data.get('event_type', 'Clinical Trial Event')  # The type of event (start, completion, etc.)
    
    # Create prompt for LLM
    prompt = f"""
    Analyze the investor sentiment and financial implications of this clinical trial event for {ticker}.
    
    CLINICAL TRIAL INFORMATION:
    - Event Type: {event_type}
    - Trial Title: {title}
    - Phase: {phase}
    - Status: {status}
    - Event Date: {event_date.strftime('%Y-%m-%d')}
    
    STOCK PRICE REACTION:
    - Pre-Event Change ({impact_result['window']} days before): {price_metrics['pre_event_change']:.2f}%
    - Post-Event Change ({impact_result['window']} days after): {price_metrics['post_event_change']:.2f}%
    - Total Window Change: {price_metrics['total_change']:.2f}%
    - Volume Change: {volume_metrics['vol_change_pct']:.2f}%
    - Volatility Change: {volatility_metrics['volatility_change']:.2f}%
    """
    
    # Add sector comparison if available
    if sector_comparison:
        prompt += f"""
    SECTOR COMPARISON (vs. {sector_comparison['ticker']}):
    - Sector Pre-Event Change: {sector_comparison['pre_event_change']:.2f}%
    - Sector Post-Event Change: {sector_comparison['post_event_change']:.2f}%
    - Relative Performance (Pre-Event): {sector_comparison['relative_pre']:.2f}%
    - Relative Performance (Post-Event): {sector_comparison['relative_post']:.2f}%
    """
    
    # Analysis instructions
    prompt += """
    Based on this data, please provide an analysis of:
    1. The likely investor sentiment before and after this clinical trial event
    2. How this event compares to typical market reactions for this type of trial/phase
    3. The financial implications for the company
    4. Any potential strategic takeaways for investors
    
    Please focus specifically on what the stock price movement suggests about market perception.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Unable to generate sentiment analysis: {str(e)}"

def analyze_trial_event_impact(stock_data: pd.DataFrame, event_date: datetime.datetime, 
                             window_days_before: int = 15, window_days_after: int = 15,
                             event_name: str = "Trial Event") -> Dict:
    """
    Analyze stock price changes before and after a clinical trial event.
    This function compares price, volume, and volatility metrics in the windows
    before and after a specific clinical trial milestone date.
    
    Args:
        stock_data: DataFrame with historical stock data
        event_date: Date of the trial event
        window_days_before: Number of days to analyze before the event
        window_days_after: Number of days to analyze after the event
        event_name: Name of the event for reporting
        
    Returns:
        Dictionary with comprehensive analysis results
    """
    # Handle potential errors
    if stock_data is None or stock_data.empty:
        return {"error": "No stock data available for analysis"}
    
    # Convert event_date to pandas Timestamp
    event_date = pd.Timestamp(event_date)
    
    # Handle timezone issues
    is_tz_aware = stock_data.index.tzinfo is not None
    if is_tz_aware and event_date.tzinfo is None:
        # If stock data is tz-aware but event date is naive, 
        # localize event_date to the same timezone as stock_data
        stock_tz = stock_data.index[0].tzinfo
        event_date = event_date.tz_localize(stock_tz)
    elif not is_tz_aware and event_date.tzinfo is not None:
        # If stock data is naive but event date is tz-aware,
        # make the event_date naive
        event_date = event_date.tz_localize(None)
    
    # Define window boundaries
    pre_start = event_date - pd.Timedelta(days=window_days_before + 5)  # Add buffer for weekends/holidays
    pre_end = event_date - pd.Timedelta(days=1)
    post_start = event_date + pd.Timedelta(days=1)
    post_end = event_date + pd.Timedelta(days=window_days_after + 5)  # Add buffer for weekends/holidays
    
    # Get pre and post event data with proper filtering
    pre_event_data = stock_data[(stock_data.index >= pre_start) & (stock_data.index <= pre_end)]
    post_event_data = stock_data[(stock_data.index >= post_start) & (stock_data.index <= post_end)]
    
    # Limit to the exact window size if we have more trading days than needed
    if len(pre_event_data) > window_days_before:
        pre_event_data = pre_event_data.iloc[-window_days_before:]
    
    if len(post_event_data) > window_days_after:
        post_event_data = post_event_data.iloc[:window_days_after]
    
    # Verify we have enough data
    if len(pre_event_data) < 3 or len(post_event_data) < 3:
        return {
            "error": f"Insufficient data around event date {event_date.strftime('%Y-%m-%d')}. " 
                     f"Found {len(pre_event_data)} days before and {len(post_event_data)} days after."
        }
    
    # Calculate price metrics
    try:
        # Start and end prices for each window
        pre_start_price = pre_event_data['Close'].iloc[0]
        pre_end_price = pre_event_data['Close'].iloc[-1]
        post_start_price = post_event_data['Close'].iloc[0]
        post_end_price = post_event_data['Close'].iloc[-1]
        event_price = post_start_price  # Use first price after event as the event price
        
        # Price statistics
        pre_avg_price = pre_event_data['Close'].mean()
        post_avg_price = post_event_data['Close'].mean()
        pre_max_price = pre_event_data['Close'].max()
        post_max_price = post_event_data['Close'].max()
        pre_min_price = pre_event_data['Close'].min()
        post_min_price = post_event_data['Close'].min()
        
        # Calculate price changes
        pre_window_change_pct = ((pre_end_price - pre_start_price) / pre_start_price) * 100
        post_window_change_pct = ((post_end_price - post_start_price) / post_start_price) * 100
        overall_change_pct = ((post_end_price - pre_start_price) / pre_start_price) * 100
        event_day_change_pct = ((post_start_price - pre_end_price) / pre_end_price) * 100
        
        # Price metrics dictionary
        price_metrics = {
            'pre_start_price': pre_start_price,
            'pre_end_price': pre_end_price,
            'event_price': event_price,
            'post_start_price': post_start_price,
            'post_end_price': post_end_price,
            'pre_window_change_pct': pre_window_change_pct,
            'post_window_change_pct': post_window_change_pct,
            'event_day_change_pct': event_day_change_pct,
            'overall_change_pct': overall_change_pct,
            'pre_avg_price': pre_avg_price,
            'post_avg_price': post_avg_price,
            'pre_max_price': pre_max_price,
            'post_max_price': post_max_price,
            'pre_min_price': pre_min_price,
            'post_min_price': post_min_price,
            'avg_price_change_pct': ((post_avg_price - pre_avg_price) / pre_avg_price) * 100
        }
    except Exception as e:
        return {"error": f"Error calculating price metrics: {str(e)}"}
    
    # Calculate volume metrics
    try:
        pre_avg_volume = pre_event_data['Volume'].mean()
        post_avg_volume = post_event_data['Volume'].mean()
        pre_max_volume = pre_event_data['Volume'].max()
        post_max_volume = post_event_data['Volume'].max()
        
        # Volume change as percentage
        volume_change_pct = ((post_avg_volume - pre_avg_volume) / pre_avg_volume) * 100 if pre_avg_volume > 0 else 0
        max_volume_change_pct = ((post_max_volume - pre_max_volume) / pre_max_volume) * 100 if pre_max_volume > 0 else 0
        
        # Volume metrics dictionary
        volume_metrics = {
            'pre_avg_volume': pre_avg_volume,
            'post_avg_volume': post_avg_volume,
            'pre_max_volume': pre_max_volume,
            'post_max_volume': post_max_volume,
            'volume_change_pct': volume_change_pct,
            'max_volume_change_pct': max_volume_change_pct
        }
    except Exception as e:
        volume_metrics = {"error": f"Error calculating volume metrics: {str(e)}"}
    
    # Calculate volatility and returns metrics
    try:
        # Daily returns statistics
        pre_avg_return = pre_event_data['Daily Return'].mean() if 'Daily Return' in pre_event_data.columns else None
        post_avg_return = post_event_data['Daily Return'].mean() if 'Daily Return' in post_event_data.columns else None
        pre_return_volatility = pre_event_data['Daily Return'].std() if 'Daily Return' in pre_event_data.columns else None
        post_return_volatility = post_event_data['Daily Return'].std() if 'Daily Return' in post_event_data.columns else None
        
        # Calculate changes in volatility
        volatility_change_pct = ((post_return_volatility - pre_return_volatility) / pre_return_volatility) * 100 if pre_return_volatility and pre_return_volatility > 0 else None
        
        # Returns and volatility metrics dictionary
        returns_metrics = {
            'pre_avg_return': pre_avg_return,
            'post_avg_return': post_avg_return,
            'pre_return_volatility': pre_return_volatility,
            'post_return_volatility': post_return_volatility,
            'volatility_change_pct': volatility_change_pct,
            'return_change': post_avg_return - pre_avg_return if pre_avg_return is not None and post_avg_return is not None else None
        }
    except Exception as e:
        returns_metrics = {"error": f"Error calculating returns metrics: {str(e)}"}
    
    # Calculate statistical significance using t-test
    try:
        from scipy import stats
        
        # Ensure we have enough data for a meaningful test
        if len(pre_event_data) >= 5 and len(post_event_data) >= 5 and 'Daily Return' in pre_event_data.columns:
            pre_returns = pre_event_data['Daily Return'].dropna()
            post_returns = post_event_data['Daily Return'].dropna()
            
            if len(pre_returns) >= 3 and len(post_returns) >= 3:
                t_stat, p_value = stats.ttest_ind(pre_returns, post_returns, equal_var=False)
                
                statistical_test = {
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'is_significant': p_value < 0.05,
                    'confidence_level': (1 - p_value) * 100 if p_value < 1 else 0
                }
            else:
                statistical_test = {
                    'error': "Not enough non-NaN return values for t-test"
                }
        else:
            statistical_test = {
                'error': "Not enough data for statistical testing"
            }
    except Exception as e:
        statistical_test = {"error": f"Error in statistical testing: {str(e)}"}
    
    # Assemble complete results dictionary
    result = {
        'event_date': event_date,
        'event_name': event_name,
        'window_days_before': window_days_before,
        'window_days_after': window_days_after,
        'data_points_before': len(pre_event_data),
        'data_points_after': len(post_event_data),
        'price_metrics': price_metrics,
        'volume_metrics': volume_metrics,
        'returns_metrics': returns_metrics,
        'statistical_test': statistical_test,
        'pre_event_data': pre_event_data,
        'post_event_data': post_event_data
    }
    
    # Add an impact assessment summary
    if abs(price_metrics['event_day_change_pct']) > 5:
        impact_level = "Strong"
    elif abs(price_metrics['event_day_change_pct']) > 2:
        impact_level = "Moderate"
    else:
        impact_level = "Weak"
        
    direction = "Positive" if price_metrics['post_window_change_pct'] > 0 else "Negative"
    
    result['impact_summary'] = {
        'level': impact_level,
        'direction': direction,
        'description': f"{impact_level} {direction} impact observed with {price_metrics['post_window_change_pct']:.2f}% price change after event"
    }
    
    return result 

def plot_event_impact(impact_result: Dict, ticker: str = None) -> plt.Figure:
    """
    Create a visualization of stock price movement before and after a clinical trial event.
    
    Args:
        impact_result: Dictionary with analysis results from analyze_trial_event_impact
        ticker: Stock ticker symbol (optional)
        
    Returns:
        Matplotlib figure with the visualization
    """
    # Check if the analysis result is valid
    if "error" in impact_result:
        raise ValueError(f"Cannot create visualization: {impact_result['error']}")
    
    # Extract data from the impact result
    event_date = impact_result['event_date']
    event_name = impact_result['event_name']
    pre_event_data = impact_result['pre_event_data']
    post_event_data = impact_result['post_event_data']
    price_metrics = impact_result['price_metrics']
    
    # Combine data for continuous visualization
    all_data = pd.concat([pre_event_data, post_event_data])
    
    # Create figure with two subplots - price and volume
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    
    # Plot price data on top subplot
    ax1.plot(pre_event_data.index, pre_event_data['Close'], label='Pre-Event', color='blue', linewidth=1.5)
    ax1.plot(post_event_data.index, post_event_data['Close'], label='Post-Event', color='green', linewidth=1.5)
    
    # Add event day marker
    ax1.axvline(x=event_date, color='red', linestyle='--', linewidth=2, alpha=0.8)
    
    # Shade the pre and post event areas
    pre_alpha = 0.15
    post_alpha = 0.15
    
    ax1.axvspan(pre_event_data.index[0], pre_event_data.index[-1], alpha=pre_alpha, color='blue')
    ax1.axvspan(post_event_data.index[0], post_event_data.index[-1], alpha=post_alpha, color='green')
    
    # Add price change annotations
    y_max = all_data['Close'].max()
    y_min = all_data['Close'].min()
    y_range = y_max - y_min
    
    # Add pre-event change
    pre_change_text = f"Pre-Event: {price_metrics['pre_window_change_pct']:.2f}%"
    ax1.annotate(pre_change_text, 
                xy=(pre_event_data.index[len(pre_event_data)//2], pre_event_data['Close'].mean()),
                xytext=(pre_event_data.index[len(pre_event_data)//2], y_max - y_range * 0.1),
                ha='center', va='bottom',
                bbox=dict(boxstyle="round,pad=0.3", fc="lightblue", alpha=0.8))
    
    # Add post-event change
    post_change_text = f"Post-Event: {price_metrics['post_window_change_pct']:.2f}%"
    post_color = "lightgreen" if price_metrics['post_window_change_pct'] > 0 else "lightcoral"
    ax1.annotate(post_change_text, 
                xy=(post_event_data.index[len(post_event_data)//2], post_event_data['Close'].mean()),
                xytext=(post_event_data.index[len(post_event_data)//2], y_max - y_range * 0.1),
                ha='center', va='bottom',
                bbox=dict(boxstyle="round,pad=0.3", fc=post_color, alpha=0.8))
    
    # Add event marker annotation
    ax1.annotate(event_name, 
                xy=(event_date, all_data['Close'].max()),
                xytext=(event_date, y_max + y_range * 0.05),
                ha='center', va='bottom',
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.2"),
                bbox=dict(boxstyle="round,pad=0.3", fc="red", alpha=0.6, color="white"))
    
    # Add statistical significance if available
    if 'statistical_test' in impact_result and 'p_value' in impact_result['statistical_test']:
        p_value = impact_result['statistical_test']['p_value']
        significance_text = f"Statistical Significance: p={p_value:.4f}"
        
        if p_value < 0.05:
            significance_text += " (Significant)"
            text_color = "green"
        else:
            significance_text += " (Not Significant)"
            text_color = "gray"
            
        # Place at the top right corner
        ax1.annotate(significance_text,
                    xy=(0.98, 0.05),
                    xycoords='axes fraction',
                    ha='right', va='bottom',
                    color=text_color,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8))
    
    # Plot volume on lower subplot
    ax2.bar(pre_event_data.index, pre_event_data['Volume'], color='blue', alpha=0.6, label='Pre-Event Volume')
    ax2.bar(post_event_data.index, post_event_data['Volume'], color='green', alpha=0.6, label='Post-Event Volume')
    
    # Add event line to volume plot
    ax2.axvline(x=event_date, color='red', linestyle='--', linewidth=2, alpha=0.8)
    
    # Format and label axes
    title = f"Impact of {event_name} on Stock Price"
    if ticker:
        title += f" ({ticker})"
    
    ax1.set_title(title, fontsize=16)
    ax1.set_ylabel("Price ($)", fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    
    ax2.set_xlabel("Date", fontsize=12)
    ax2.set_ylabel("Volume", fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # Add impact summary at the bottom
    if 'impact_summary' in impact_result:
        impact_summary = impact_result['impact_summary']
        summary_text = impact_summary['description']
        
        fig.text(0.5, 0.01, summary_text, ha='center', va='bottom', 
                bbox=dict(boxstyle="round,pad=0.3", fc="lightyellow", alpha=0.8),
                fontsize=12)
    
    # Format dates on x-axis
    plt.xticks(rotation=45)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.12)  # Make room for the summary text
    
    return fig

def test_granger_causality(stock_data: pd.DataFrame, trial_dates: List[datetime.datetime], 
                        max_lag: int = 10, min_lag: int = 1) -> Dict:
    """
    Test if clinical trial events Granger-cause stock price changes.
    
    Args:
        stock_data: DataFrame with daily stock prices 
        trial_dates: List of dates of trial events
        max_lag: Maximum lag (in trading days) to test
        min_lag: Minimum lag (in trading days) to test
        
    Returns:
        Dictionary with test results
    """
    try:
        # We need statsmodels for this test
        from statsmodels.tsa.stattools import grangercausalitytests
        
        # Convert all dates to pandas Timestamps with consistent timezone
        formatted_dates = []
        for date in trial_dates:
            if date is None:
                continue
                
            # Parse string dates if needed
            if isinstance(date, str):
                try:
                    # Try common date formats
                    for fmt in ['%Y-%m-%d', '%B %Y', '%b %d, %Y']:
                        try:
                            date_obj = datetime.datetime.strptime(date, fmt)
                            date = date_obj
                            break
                        except ValueError:
                            continue
                except Exception:
                    # Skip dates that can't be parsed
                    continue
            
            # Convert to Timestamp
            if isinstance(date, datetime.datetime):
                date = pd.Timestamp(date)
                
                # Handle timezone consistently
                is_tz_aware = stock_data.index.tzinfo is not None
                if is_tz_aware and date.tzinfo is None:
                    stock_tz = stock_data.index[0].tzinfo
                    date = date.tz_localize(stock_tz)
                elif not is_tz_aware and date.tzinfo is not None:
                    date = date.tz_localize(None)
                    
                formatted_dates.append(date)
        
        # Create binary event series (1 on event days, 0 otherwise)
        event_series = pd.Series(0, index=stock_data.index)
        for date in formatted_dates:
            # Find the closest trading day if the exact date isn't in the index
            if date in event_series.index:
                event_series[date] = 1
            else:
                # Find closest trading day after the event
                future_dates = stock_data.index[stock_data.index > date]
                if len(future_dates) > 0:
                    closest_date = future_dates[0]
                    event_series[closest_date] = 1
        
        # Ensure we have at least one event in the series
        if event_series.sum() == 0:
            return {
                "error": "No events found in stock data timeframe",
                "recommendation": "Try with a longer stock data window or different event dates"
            }
        
        # Prepare data for Granger causality test
        # We want to test if events (X) cause stock returns (Y)
        stock_returns = stock_data['Daily Return'].fillna(0)
        
        # Combine into a DataFrame
        data = pd.DataFrame({
            'events': event_series,
            'returns': stock_returns
        })
        
        # Drop any remaining NAs
        data = data.dropna()
        
        # Ensure we have enough data
        if len(data) < max_lag + 10:
            return {
                "error": f"Not enough data for testing with max_lag={max_lag}",
                "recommendation": "Try with a shorter max_lag or more stock data"
            }
        
        # Run Granger causality test
        # Test if events (X) cause returns (Y)
        # Format: grangercausalitytests(data, maxlag, verbose)
        max_lag = min(max_lag, len(data) // 5)  # Ensure lag isn't too large compared to data
        gc_test_results = grangercausalitytests(data[['events', 'returns']], maxlag=max_lag, verbose=False)
        
        # Extract results and find the best lag
        results = {}
        best_p_value = 1.0
        best_lag = None
        
        for lag in range(min_lag, max_lag + 1):
            # Get p-value from F-test
            p_value = gc_test_results[lag][0]['ssr_ftest'][1]
            f_stat = gc_test_results[lag][0]['ssr_ftest'][0]
            
            results[lag] = {
                'p_value': p_value,
                'f_statistic': f_stat,
                'significant': p_value < 0.05
            }
            
            # Track best lag (lowest p-value)
            if p_value < best_p_value:
                best_p_value = p_value
                best_lag = lag
        
        # Create summary results
        significant_lags = [lag for lag, result in results.items() if result['significant']]
        has_causality = len(significant_lags) > 0
        
        summary = {
            'has_granger_causality': has_causality,
            'significant_lags': significant_lags,
            'best_lag': best_lag,
            'best_p_value': best_p_value,
            'lag_results': results,
            'interpretation': (
                f"Trial events appear to Granger-cause stock price changes with {len(significant_lags)} "
                f"significant lag periods (best: {best_lag} days, p={best_p_value:.4f})"
                if has_causality else
                f"No significant Granger-causality found between trial events and stock price changes "
                f"(best lag: {best_lag} days, p={best_p_value:.4f})"
            ),
            'events_tested': int(event_series.sum()),
            'recommendation': (
                "Consider incorporating trial event information into trading strategy "
                f"with a {best_lag}-day window"
                if has_causality else
                "Trial events do not appear to provide predictive value for stock movement"
            )
        }
        
        return summary
        
    except ImportError:
        return {
            "error": "Missing required package: statsmodels",
            "recommendation": "Install statsmodels with 'pip install statsmodels'"
        }
    except Exception as e:
        return {
            "error": f"Error in Granger causality test: {str(e)}",
            "recommendation": "Check data format and try with different parameters"
        }

def group_trials_by_sponsor_disease(studies: List[Dict]) -> Dict:
    """
    Group clinical trials by sponsor and disease for aggregated analysis.
    
    Args:
        studies: List of study dictionaries
        
    Returns:
        Dictionary with sponsor-disease pairs and associated trials
    """
    grouped_trials = {}
    
    for study in studies:
        sponsor = study.get('sponsor', 'Unknown')
        conditions = study.get('conditions', 'Unknown')
        
        # Skip if missing critical data
        if sponsor == 'Unknown' or conditions == 'Unknown' or sponsor == 'N/A' or conditions == 'N/A':
            continue
        
        # Handle ticker
        ticker = study.get('ticker')
        
        # Skip studies without ticker for financial analysis
        if not ticker:
            continue
            
        # Create condition list
        if isinstance(conditions, str):
            condition_list = [c.strip() for c in conditions.split(',')]
        else:
            condition_list = [conditions]
        
        # Add to groups
        for condition in condition_list:
            # Skip empty conditions
            if not condition or condition.strip() == '':
                continue
                
            # Clean condition name
            condition = condition.strip()
            
            key = (sponsor, condition)
            if key not in grouped_trials:
                grouped_trials[key] = {
                    'sponsor': sponsor,
                    'condition': condition,
                    'ticker': ticker,
                    'trials': [],
                    'event_dates': []
                }
            
            # Add trial info
            trial_info = {
                'nct_id': study.get('nct_id', 'N/A'),
                'brief_title': study.get('brief_title', 'N/A'),
                'phase': study.get('phase', 'N/A'),
                'start_date': study.get('start_date'),
                'completion_date': study.get('completion_date'),
                'primary_completion_date': study.get('primary_completion_date'),
                'status': study.get('status', 'N/A')
            }
            
            # Only add if this trial isn't already in the group
            if not any(t.get('nct_id') == trial_info['nct_id'] for t in grouped_trials[key]['trials']):
                grouped_trials[key]['trials'].append(trial_info)
            
                # Add event dates for timeline analysis
                for date_field, event_type in [
                    ('start_date', 'Trial Start'),
                    ('completion_date', 'Trial Completion'),
                    ('primary_completion_date', 'Primary Completion')
                ]:
                    if study.get(date_field):
                        grouped_trials[key]['event_dates'].append({
                            'date': study.get(date_field),
                            'event_type': event_type,
                            'nct_id': study.get('nct_id', 'N/A')
                        })
    
    # Remove groups with only one trial - less useful for aggregated analysis
    filtered_groups = {k: v for k, v in grouped_trials.items() if len(v['trials']) > 1}
    
    return filtered_groups

def analyze_grouped_trials_impact(grouped_trials: Dict, window_days: int = 15) -> Dict:
    """
    Analyze stock impact across multiple trials for the same sponsor-disease pair.
    
    Args:
        grouped_trials: Dictionary from group_trials_by_sponsor_disease
        window_days: Number of days to analyze before/after events
        
    Returns:
        Dictionary with analysis results for each group
    """
    results = {}
    
    for key, group in grouped_trials.items():
        sponsor, condition = key
        ticker = group.get('ticker')
        
        if not ticker:
            continue
        
        # Check if we have event dates
        if not group['event_dates']:
            continue
            
        # Find earliest and latest dates
        all_dates = []
        for event in group['event_dates']:
            try:
                # Handle different date formats
                date_str = event['date']
                for fmt in ['%Y-%m-%d', '%B %Y', '%b %d, %Y']:
                    try:
                        date = datetime.datetime.strptime(date_str, fmt)
                        all_dates.append(date)
                        break
                    except ValueError:
                        continue
            except:
                continue
        
        if not all_dates:
            continue
            
        # Convert to pandas Timestamps
        all_dates = [pd.Timestamp(d) for d in all_dates]
            
        min_date = min(all_dates) - pd.Timedelta(days=window_days*2)
        max_date = max(all_dates) + pd.Timedelta(days=window_days*2)
        
        # Calculate days needed
        days_needed = (max_date - min_date).days + 30  # Add buffer
        
        # Fetch stock data
        stock_data = fetch_stock_data(ticker, days=days_needed)
        
        if stock_data is None or stock_data.empty:
            continue
        
        # Analyze impact for each event
        event_impacts = []
        for event in group['event_dates']:
            try:
                # Parse date
                date_str = event['date']
                event_date = None
                
                for fmt in ['%Y-%m-%d', '%B %Y', '%b %d, %Y']:
                    try:
                        event_date = datetime.datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if event_date:
                    # Analyze impact
                    impact = analyze_trial_event_impact(
                        stock_data, 
                        event_date, 
                        window_days_before=window_days, 
                        window_days_after=window_days,
                        event_name=event['event_type']
                    )
                    
                    # Add event metadata
                    if "error" not in impact:
                        impact['event_type'] = event['event_type']
                        impact['nct_id'] = event['nct_id']
                        impact['date_str'] = date_str
                        event_impacts.append(impact)
            except Exception as e:
                continue
        
        # Calculate aggregated metrics
        if event_impacts:
            # Price metrics
            avg_pre_change = sum(impact['price_metrics']['pre_window_change_pct'] for impact in event_impacts) / len(event_impacts)
            avg_post_change = sum(impact['price_metrics']['post_window_change_pct'] for impact in event_impacts) / len(event_impacts)
            avg_event_day_change = sum(impact['price_metrics']['event_day_change_pct'] for impact in event_impacts) / len(event_impacts)
            
            # Volume metrics
            avg_volume_change = sum(impact['volume_metrics']['volume_change_pct'] for impact in event_impacts) / len(event_impacts)
            
            # Volatility metrics
            volatility_changes = []
            for impact in event_impacts:
                if impact['returns_metrics'].get('volatility_change_pct') is not None:
                    volatility_changes.append(impact['returns_metrics']['volatility_change_pct'])
            
            avg_volatility_change = sum(volatility_changes) / len(volatility_changes) if volatility_changes else None
            
            # Count significant events
            significant_count = sum(1 for impact in event_impacts 
                                   if 'statistical_test' in impact 
                                   and impact['statistical_test'].get('is_significant', False))
            
            significance_ratio = significant_count / len(event_impacts) if event_impacts else 0
            
            # Group events by type
            events_by_type = {}
            for impact in event_impacts:
                event_type = impact['event_type']
                if event_type not in events_by_type:
                    events_by_type[event_type] = []
                events_by_type[event_type].append(impact)
            
            # Calculate statistics by event type
            event_type_stats = {}
            for event_type, impacts in events_by_type.items():
                if impacts:
                    avg_type_post_change = sum(impact['price_metrics']['post_window_change_pct'] for impact in impacts) / len(impacts)
                    event_type_stats[event_type] = {
                        'count': len(impacts),
                        'avg_post_change': avg_type_post_change,
                        'significant_count': sum(1 for impact in impacts 
                                              if 'statistical_test' in impact 
                                              and impact['statistical_test'].get('is_significant', False)),
                    }
            
            # Create results dictionary
            results[key] = {
                'sponsor': sponsor,
                'condition': condition,
                'ticker': ticker,
                'trial_count': len(group['trials']),
                'event_count': len(event_impacts),
                'avg_price_change': {
                    'pre_window': avg_pre_change,
                    'post_window': avg_post_change,
                    'event_day': avg_event_day_change
                },
                'avg_volume_change': avg_volume_change,
                'avg_volatility_change': avg_volatility_change,
                'significant_events': significant_count,
                'significance_ratio': significance_ratio,
                'event_type_stats': event_type_stats,
                'individual_impacts': event_impacts,
                'earliest_date': min(all_dates),
                'latest_date': max(all_dates)
            }
            
            # Add an overall assessment
            if avg_post_change > 2:
                results[key]['assessment'] = "Positive trend observed across multiple trials"
            elif avg_post_change < -2:
                results[key]['assessment'] = "Negative trend observed across multiple trials"
            else:
                results[key]['assessment'] = "No consistent impact pattern across trials"
                
            # Identify most impactful event type
            if event_type_stats:
                most_impactful_type = max(event_type_stats.items(), 
                                        key=lambda x: abs(x[1]['avg_post_change']))
                results[key]['most_impactful_event'] = {
                    'type': most_impactful_type[0],
                    'avg_change': most_impactful_type[1]['avg_post_change'],
                    'count': most_impactful_type[1]['count']
                }
            
            # Run Granger causality test if we have enough events
            if len(event_impacts) >= 3:
                # Extract all event dates
                event_dates = [impact['event_date'] for impact in event_impacts]
                causality_result = test_granger_causality(stock_data, event_dates)
                results[key]['granger_causality'] = causality_result
    
    return results