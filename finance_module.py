import json
import os
import datetime
import pandas as pd
import yfinance as yf
import streamlit as st
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Any

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

# Fetch stock data for a given ticker with fallback options for problematic tickers
def fetch_stock_data(ticker: str, days: int = 90) -> Optional[pd.DataFrame]:
    """
    Fetch stock data for a given ticker with fallback options for problematic tickers.
    
    Args:
        ticker: The stock ticker symbol
        days: Number of days of historical data to fetch
        
    Returns:
        DataFrame with stock data or None if the fetch failed
    """
    try:
        # Calculate start and end dates
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        stock_data = pd.DataFrame()
        
        # Handle problematic tickers with alternative versions
        if ticker in ["AZN", "BMY"]:
            alternative_tickers = {
                "AZN": ["AZN.L", "AZNCF"], # London Exchange and OTC
                "BMY": ["BMY.MX", "BMYQF"]  # Mexico Exchange and OTC
            }
            
            st.info(f"Trying alternative tickers for {ticker}...")
            
            for alt_ticker in alternative_tickers.get(ticker, []):
                try:
                    alt_stock_data = yf.download(alt_ticker, 
                                          start=start_date, 
                                          end=end_date, 
                                          progress=False)
                    if not alt_stock_data.empty:
                        st.success(f"Successfully fetched data using alternative ticker {alt_ticker}")
                        stock_data = alt_stock_data
                        break
                except Exception as e:
                    st.warning(f"Failed with alternative ticker {alt_ticker}: {e}")
                    continue
        
        # If no alternative worked or not a problematic ticker, try the original
        if stock_data.empty:
            stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if stock_data.empty:
            st.warning(f"No stock data available for ticker {ticker}")
            return None
            
        # Calculate additional metrics
        stock_data['Daily Return'] = stock_data['Close'].pct_change() * 100
        stock_data['7-Day MA'] = stock_data['Close'].rolling(window=7).mean()
        stock_data['30-Day MA'] = stock_data['Close'].rolling(window=30).mean()
        
        return stock_data
    except Exception as e:
        st.warning(f"Error fetching stock data for {ticker}: {e}")
        return None

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

# Add financial data to clinical trial studies
def enrich_studies_with_financial_data(studies: List[Dict]) -> List[Dict]:
    """
    Enrich the clinical trial studies with financial data.
    
    Args:
        studies: List of dictionaries containing study data
        
    Returns:
        List of dictionaries with enriched data
    """
    enriched_studies = []
    
    for study in studies:
        enriched_study = study.copy()
        
        # Extract sponsor
        sponsor = study.get('sponsor', 'N/A')
        
        # Try to match sponsor to ticker
        ticker = match_company_to_ticker(sponsor)
        
        if ticker:
            # Store the ticker
            enriched_study['ticker'] = ticker
            
            # Fetch stock data (in a real app, could batch this to avoid redundant fetches)
            stock_data = fetch_stock_data(ticker)
            
            if stock_data is not None:
                # Calculate market metrics
                metrics = calculate_market_metrics(stock_data)
                
                # Add metrics to study data
                enriched_study['market_metrics'] = metrics
                
                # Flag that this study has financial data
                enriched_study['has_financial_data'] = True
            else:
                enriched_study['has_financial_data'] = False
        else:
            enriched_study['has_financial_data'] = False
        
        enriched_studies.append(enriched_study)
    
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
        
        # Add trial dates to the model results for visualization later
        formatted_trial_dates = []
        for date_str in trial_dates:
            if date_str:
                try:
                    # Handle different date formats
                    for fmt in ['%B %Y', '%Y-%m-%d', '%b %d, %Y']:
                        try:
                            date_obj = datetime.datetime.strptime(date_str, fmt)
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
    from app import model
    
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
    
    Your analysis should focus on the relationship between clinical milestones and potential market impact.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Unable to generate forecast analysis: {str(e)}" 