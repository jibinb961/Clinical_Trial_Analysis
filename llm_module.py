import os
import google.generativeai as genai
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables")

# Initialize Gemini client with safety settings for research/medical content
def initialize_gemini():
    """
    Initialize the Gemini API client.
    
    Returns:
        True if initialization was successful, False otherwise
    """
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        return True
    except Exception as e:
        print(f"Error initializing Gemini: {str(e)}")
        return False

def format_trials_for_prompt(trials: List[Dict], sponsor_name: str) -> str:
    """
    Format clinical trial data for a structured LLM prompt.
    
    Args:
        trials: List of clinical trial data dictionaries
        sponsor_name: Name of the sponsor company
        
    Returns:
        Formatted prompt string for Gemini
    """
    prompt = f"""
The following clinical trial data is from {sponsor_name}. Each entry includes the disease being studied,
number of participants enrolled, timeline information, and a short summary of the study. Based on this, 
generate a concise summary of what {sponsor_name} is currently focusing on in their research pipeline.

Please include:
1. The main disease areas or therapeutic focuses
2. The stages of development (based on trial phases)
3. Timeline patterns (when trials started, expected completions)
4. Any notable trends or patterns in their research

CLINICAL TRIAL DATA:
"""
    
    # Add each trial to the prompt
    for i, trial in enumerate(trials, 1):
        # Format dates for display in prompt
        start_date = trial.get('start_date', 'N/A')
        completion_date = trial.get('completion_date', 'N/A') 
        primary_completion_date = trial.get('primary_completion_date', 'N/A')
        
        prompt += f"""
Trial {i}:
- NCT ID: {trial.get('nct_id', 'N/A')}
- Disease/Condition: {trial.get('conditions', 'N/A')}
- Enrollment: {trial.get('enrollment', 'N/A')} participants
- Phase: {trial.get('phase', 'N/A')}
- Status: {trial.get('status', 'N/A')}
- Timeline: Start: {start_date}, Primary Completion: {primary_completion_date}, Full Completion: {completion_date}
- Summary: {trial.get('brief_summary', 'N/A')[:300]}...
"""
    
    # Add final instructions
    prompt += """
Based on the clinical trial data above, provide a well-structured analysis of the sponsor's current research focus.
Format your response in clear paragraphs with headings for:
- MAIN DISEASE AREAS
- DEVELOPMENT STAGES
- TIMELINE PATTERNS
- RESEARCH TRENDS
"""
    
    return prompt

def generate_sponsor_analysis(trials: List[Dict], sponsor_name: str) -> Optional[str]:
    """
    Generate an analysis of a sponsor's clinical trial portfolio using Gemini.
    
    Args:
        trials: List of clinical trial data dictionaries
        sponsor_name: Name of the sponsor company
        
    Returns:
        Generated analysis text from Gemini or None if an error occurred
    """
    if not trials:
        return "No clinical trial data available for analysis."
    
    # Initialize Gemini
    if not initialize_gemini():
        return "Unable to initialize Gemini AI. Please check your API key."
    
    try:
        # Format the prompt
        prompt = format_trials_for_prompt(trials, sponsor_name)
        
        # Use the more capable model for medical analysis
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Generate content
        response = model.generate_content(prompt)
        
        return response.text
    except Exception as e:
        print(f"Error generating analysis: {str(e)}")
        return f"Error generating analysis: {str(e)}" 