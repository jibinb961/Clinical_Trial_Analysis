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

# Fetch stock data for a given ticker
def fetch_stock_data(ticker: str, days: int = 90) -> Optional[pd.DataFrame]:
    """
    Fetch stock data for a given ticker.
    
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
        
        # Fetch the data
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