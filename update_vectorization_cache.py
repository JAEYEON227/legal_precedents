import json
import logging
import sys
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add root to sys.path to ensure we can import utils
sys.path.append(os.getcwd())

try:
    from utils.vectorizer import preprocess_data
    from utils.data_loader import save_vectorization_cache
except ImportError:
    print("Error: Could not import utils. Make sure you are running this script from the project root.")
    sys.exit(1)

def update_cache():
    print("Starting vectorization cache update...")
    
    try:
        # Load data
        # Check files exist
        if not os.path.exists("data_kcs.json") or not os.path.exists("data_moleg.json"):
            print("Error: Data files not found.")
            sys.exit(1)
            
        with open("data_kcs.json", "r", encoding="utf-8") as f:
            court_cases = json.load(f)
        with open("data_moleg.json", "r", encoding="utf-8") as f:
            tax_cases = json.load(f)
            
        print(f"Loaded {len(court_cases)} court cases and {len(tax_cases)} tax cases.")
        
        # Vectorize
        print("Running vectorization (this may take a while)...")
        # preprocess_data logs via st.sidebar which might be ignored or print to stderr in CLI
        preprocessed_data = preprocess_data(court_cases, tax_cases)
        
        # Save
        print("Saving cache file...")
        if save_vectorization_cache(preprocessed_data):
            print("Successfully updated vectorization cache.")
        else:
            print("Failed to save vectorization cache.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error updating cache: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_cache()
