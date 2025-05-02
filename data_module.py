import json
import requests
import datetime
from typing import Dict, List, Optional

# Constants
API_V2_URL = "https://clinicaltrials.gov/api/v2/studies"
MAX_RESULTS_PER_PAGE = 100

def load_ticker_mapping() -> Dict[str, str]:
    """
    Load ticker to sponsor mapping from a JSON file.
    
    Returns:
        Dictionary mapping ticker symbols to sponsor names
    """
    try:
        with open('ticker_to_sponsor.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Return a basic mapping if file not found
        return {
            "PFE": "Pfizer",
            "JNJ": "Johnson & Johnson",
            "MRK": "Merck",
            "ABBV": "AbbVie",
            "LLY": "Eli Lilly and Company",
            "NVS": "Novartis",
            "GSK": "GlaxoSmithKline",
            "SNY": "Sanofi",
            "AMGN": "Amgen",
            "BIIB": "Biogen",
            "BMY": "Bristol-Myers Squibb",
            "AZN": "AstraZeneca",
            "GILD": "Gilead Sciences",
            "REGN": "Regeneron Pharmaceuticals",
            "MRNA": "Moderna",
            "BNTX": "BioNTech",
            "VRTX": "Vertex Pharmaceuticals",
            "INCY": "Incyte",
            "ALXN": "Alexion Pharmaceuticals",
            "RHHBY": "Roche Holding AG"
        }

def map_ticker_to_sponsor(ticker: str) -> Optional[str]:
    """
    Map a ticker symbol to a sponsor company name.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Sponsor company name or None if not found
    """
    mapping = load_ticker_mapping()
    return mapping.get(ticker.upper())

def fetch_trials_for_sponsor(sponsor_name: str, start_date: datetime.date, end_date: datetime.date) -> List[Dict]:
    """
    Fetch clinical trials for a given sponsor within a date range.
    
    Args:
        sponsor_name: Name of the sponsor company
        start_date: Start date for trials
        end_date: End date for trials
        
    Returns:
        List of clinical trial data dictionaries
    """
    # Format dates for API
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    
    # Set up parameters for the API call with a simpler filter
    # After testing, it appears the API doesn't support empty range bounds
    # Use a simpler approach that is compatible with the API
    params = {
        "query.spons": sponsor_name,
        "format": "json",
        "pageSize": MAX_RESULTS_PER_PAGE,
        "countTotal": "true"
    }
    
    # Try a simpler approach first: just use the sponsor name without date filtering
    print(f"Searching for sponsor: {sponsor_name}")
    
    all_studies = []
    next_page_token = None
    
    # Fetch first page
    try:
        response = requests.get(API_V2_URL, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching data: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return []
            
        data = response.json()
        studies = data.get("studies", [])
        
        # Get total count info
        total_count = data.get("totalCount", 0)
        print(f"Found {total_count} total trials for sponsor")
        
        # Filter studies by date range in Python instead of using the API filter
        filtered_studies = []
        for study in studies:
            try:
                # Extract dates for filtering
                protocol_section = study.get("protocolSection", {})
                status_module = protocol_section.get("statusModule", {})
                
                # Get start date from startDateStruct
                start_date_struct = status_module.get("startDateStruct", {})
                start_date_value = start_date_struct.get("date")
                
                # Get completion date from completionDateStruct
                completion_date_struct = status_module.get("completionDateStruct", {})
                completion_date_value = completion_date_struct.get("date")
                
                # Skip study if start date is after our end date
                if start_date_value and is_date_after(start_date_value, end_date_str):
                    continue
                    
                # Skip study if it has a completion date and it's before our start date
                if completion_date_value and is_date_before(completion_date_value, start_date_str):
                    continue
                
                # If we reach here, the study is within our date range
                filtered_studies.append(study)
            except Exception as e:
                print(f"Error filtering study: {str(e)}")
                continue
        
        all_studies.extend(filtered_studies)
        next_page_token = data.get("nextPageToken")
        
        # Fetch additional pages if available (limit to 5 pages for simplicity)
        page_count = 1
        max_pages = 5
        
        while next_page_token and page_count < max_pages:
            params["pageToken"] = next_page_token
            response = requests.get(API_V2_URL, params=params)
            
            if response.status_code != 200:
                break
                
            data = response.json()
            studies = data.get("studies", [])
            
            # Filter these studies too
            filtered_studies = []
            for study in studies:
                try:
                    # Extract dates for filtering
                    protocol_section = study.get("protocolSection", {})
                    status_module = protocol_section.get("statusModule", {})
                    
                    # Get start date from startDateStruct
                    start_date_struct = status_module.get("startDateStruct", {})
                    start_date_value = start_date_struct.get("date")
                    
                    # Get completion date from completionDateStruct
                    completion_date_struct = status_module.get("completionDateStruct", {})
                    completion_date_value = completion_date_struct.get("date")
                    
                    # Skip study if start date is after our end date
                    if start_date_value and is_date_after(start_date_value, end_date_str):
                        continue
                        
                    # Skip study if it has a completion date and it's before our start date
                    if completion_date_value and is_date_before(completion_date_value, start_date_str):
                        continue
                    
                    # If we reach here, the study is within our date range
                    filtered_studies.append(study)
                except Exception as e:
                    print(f"Error filtering study: {str(e)}")
                    continue
            
            all_studies.extend(filtered_studies)
            next_page_token = data.get("nextPageToken")
            page_count += 1
            
        print(f"Retrieved and filtered to {len(all_studies)} trials in {page_count} pages")
        return all_studies
    
    except Exception as e:
        print(f"Error fetching trials: {str(e)}")
        return []
        
def is_date_after(date_str: str, compare_to: str) -> bool:
    """
    Check if a date string is after another date string.
    Handles various ISO 8601 formats.
    
    Args:
        date_str: Date string from API
        compare_to: Date string to compare to (yyyy-MM-dd)
        
    Returns:
        True if date_str is after compare_to
    """
    try:
        # Handle partial dates
        if len(date_str) == 4:  # yyyy
            date_year = int(date_str)
            compare_year = int(compare_to[:4])
            return date_year > compare_year
        elif len(date_str) == 7:  # yyyy-MM
            date_year, date_month = map(int, date_str.split('-'))
            compare_year, compare_month = map(int, compare_to[:7].split('-'))
            if date_year > compare_year:
                return True
            elif date_year == compare_year and date_month > compare_month:
                return True
            return False
        else:  # yyyy-MM-dd or longer
            date_obj = datetime.datetime.strptime(date_str[:10], '%Y-%m-%d')
            compare_obj = datetime.datetime.strptime(compare_to[:10], '%Y-%m-%d')
            return date_obj > compare_obj
    except Exception:
        # If we can't parse the date, assume it's not after
        return False

def is_date_before(date_str: str, compare_to: str) -> bool:
    """
    Check if a date string is before another date string.
    Handles various ISO 8601 formats.
    
    Args:
        date_str: Date string from API
        compare_to: Date string to compare to (yyyy-MM-dd)
        
    Returns:
        True if date_str is before compare_to
    """
    try:
        # Handle partial dates
        if len(date_str) == 4:  # yyyy
            date_year = int(date_str)
            compare_year = int(compare_to[:4])
            return date_year < compare_year
        elif len(date_str) == 7:  # yyyy-MM
            date_year, date_month = map(int, date_str.split('-'))
            compare_year, compare_month = map(int, compare_to[:7].split('-'))
            if date_year < compare_year:
                return True
            elif date_year == compare_year and date_month < compare_month:
                return True
            return False
        else:  # yyyy-MM-dd or longer
            date_obj = datetime.datetime.strptime(date_str[:10], '%Y-%m-%d')
            compare_obj = datetime.datetime.strptime(compare_to[:10], '%Y-%m-%d')
            return date_obj < compare_obj
    except Exception:
        # If we can't parse the date, assume it's not before
        return False

def extract_summary_data(study: Dict) -> Dict:
    """
    Extract key information from a clinical trial study.
    
    Args:
        study: Dictionary containing study data from the API
        
    Returns:
        Dictionary with extracted disease, enrollment, and summary data
    """
    protocol_section = study.get("protocolSection", {})
    
    # Extract identification info
    identification_module = protocol_section.get("identificationModule", {})
    nct_id = identification_module.get("nctId", "N/A")
    brief_title = identification_module.get("briefTitle", "N/A")
    
    # Extract brief summary
    description_module = protocol_section.get("descriptionModule", {})
    brief_summary = description_module.get("briefSummary", "N/A")
    
    # Extract enrollment
    design_module = protocol_section.get("designModule", {})
    enrollment_info = design_module.get("enrollmentInfo", {})
    enrollment = enrollment_info.get("count", 0)
    
    # Extract conditions
    conditions_module = protocol_section.get("conditionsModule", {})
    conditions = conditions_module.get("conditions", [])
    conditions_text = ", ".join(conditions) if conditions else "N/A"
    
    # Extract status and dates from statusModule
    status_module = protocol_section.get("statusModule", {})
    status = status_module.get("overallStatus", "N/A")
    
    # Extract dates properly from statusModule structs
    # The API provides dates in structured format with {date, type} fields
    start_date_struct = status_module.get("startDateStruct", {})
    start_date = start_date_struct.get("date")
    
    primary_completion_date_struct = status_module.get("primaryCompletionDateStruct", {})
    primary_completion_date = primary_completion_date_struct.get("date")
    
    completion_date_struct = status_module.get("completionDateStruct", {})
    completion_date = completion_date_struct.get("date")
    
    # Last update date is not in a struct
    last_update_date = status_module.get("lastUpdateSubmitDate")
    
    # Add debug output for dates
    print(f"NCT ID: {nct_id}, Start Date: {start_date}, Completion Date: {completion_date}")
    
    # Extract phase
    phases = design_module.get("phases", [])
    phase = ", ".join(phases) if phases else "N/A"
    
    return {
        "nct_id": nct_id,
        "brief_title": brief_title,
        "brief_summary": brief_summary,
        "enrollment": enrollment,
        "conditions": conditions_text,
        "status": status,
        "start_date": start_date,
        "primary_completion_date": primary_completion_date,
        "completion_date": completion_date,
        "last_update_date": last_update_date,
        "phase": phase
    }

def process_trials_for_analysis(sponsor_name: str, start_date: datetime.date, end_date: datetime.date, max_trials: int = 10, sort_by: str = "enrollment") -> List[Dict]:
    """
    Process clinical trials for a given sponsor and prepare data for LLM analysis.
    
    Args:
        sponsor_name: Name of the sponsor company
        start_date: Start date for trials
        end_date: End date for trials
        max_trials: Maximum number of trials to process
        sort_by: Field to sort by ('enrollment', 'start_date', or 'completion_date')
        
    Returns:
        List of processed trial data dictionaries ready for analysis
    """
    # Fetch trials for the sponsor within the date range
    raw_trials = fetch_trials_for_sponsor(sponsor_name, start_date, end_date)
    
    if not raw_trials:
        return []
    
    # Extract summary data from each trial
    processed_trials = []
    
    for study in raw_trials:
        trial_data = extract_summary_data(study)
        processed_trials.append(trial_data)
    
    # Define sorting function
    def get_sort_key(trial, field):
        # For dates, convert string to datetime if possible, otherwise use a default value
        if field in ['start_date', 'completion_date', 'primary_completion_date']:
            value = trial.get(field)
            if value and isinstance(value, str):
                try:
                    # Handle various ISO 8601 date formats
                    if len(value) == 4:  # yyyy
                        return f"{value}-01-01"  # Use January 1st
                    elif len(value) == 7:  # yyyy-MM
                        return f"{value}-01"  # Use 1st day of month
                    else:  # yyyy-MM-dd or longer
                        return value[:10]  # Use first 10 chars (date part)
                except:
                    return "9999-12-31"  # Future date as default
            return "9999-12-31"  # Future date as default
        
        # For enrollment, use the number or 0 if not available
        if field == 'enrollment':
            value = trial.get(field, 0)
            if isinstance(value, str):
                try:
                    return int(value)
                except:
                    return 0
            return value
        
        # For any other field, use the field value directly
        return trial.get(field, "")
    
    # Sort the trials based on the selected field
    if sort_by == 'start_date':
        # Sort by start date in descending order (most recent first)
        processed_trials.sort(key=lambda x: get_sort_key(x, 'start_date'), reverse=True)
    elif sort_by == 'completion_date':
        # Sort by expected completion date in ascending order (soonest first)
        processed_trials.sort(key=lambda x: get_sort_key(x, 'completion_date'))
    else:  # Default to enrollment
        # Sort by enrollment in descending order (largest first)
        processed_trials.sort(key=lambda x: get_sort_key(x, 'enrollment'), reverse=True)
    
    # Return the top trials based on max_trials parameter
    return processed_trials[:max_trials] 