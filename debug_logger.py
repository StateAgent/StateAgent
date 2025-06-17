# --- START OF FILE debug_logger.py ---

import os
import json
import datetime

# Create a 'logs' directory if it doesn't exist
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "prompt_log.json")

def log_prompt(payload):
    """
    Logs the full LLM payload to a file for debugging.
    This provides a "mind's eye" view of what the agent is thinking.
    """
    try:
        # Create a log entry with a timestamp
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "payload": payload
        }
        
        # Append the JSON object to the log file
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, indent=2))
            f.write(",\n") # Add a comma and newline for JSON array structure
            
        print(f"[DEBUG_LOGGER] Prompt for model '{payload.get('model')}' saved to '{LOG_FILE}'.")

    except Exception as e:
        print(f"[DEBUG_LOGGER_ERROR] Failed to log prompt: {e}")

# --- END OF FILE debug_logger.py ---