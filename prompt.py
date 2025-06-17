# --- START OF FILE prompt.py ---
import os
import yaml
import serverconfig # <-- The missing import that caused the crash.

PERSONA_CARDS, ABILITY_CARDS, ENGINE_CARDS = {}, {}, {}

def _load_cards_from_dir(directory, card_dict, extension, content_attr):
    """Generic function to load cards with a custom YAML extension."""
    if not os.path.exists(directory):
        # This is expected on first run, we'll create the dirs in server.py
        return
    
    dir_name = os.path.basename(directory)
    for filename in os.listdir(directory):
        if not filename.endswith(extension):
            continue
        
        # Extract ID (e.g., "AA" from "AA_librarian.persona.yaml")
        card_id = os.path.splitext(os.path.splitext(filename)[0])[0].split('_', 1)[0].upper()
        
        try:
            with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
                # Validate the card has the required keys
                if data and "name" in data and content_attr in data:
                    card_dict[card_id] = data
                    print(f"  - Loaded [{dir_name}] '{card_id}': {data['name']}")
                else:
                    print(f"[PROMPT_MGR_WARN] Skipping '{filename}': missing 'name' or '{content_attr}' key.")

        except Exception as e:
            print(f"ERROR loading card {filename}: {e}")

def load_all_cards():
    """Loads all card types from their respective subdirectories."""
    print("[PROMPT_MGR] Reloading all prompt cards from YAML files...")
    # Clear the dictionaries to ensure a fresh load on reload
    PERSONA_CARDS.clear(); ABILITY_CARDS.clear(); ENGINE_CARDS.clear()
    
    # Use the PROMPTS_DIR from our new serverconfig
    base_dir = serverconfig.PROMPTS_DIR
    
    _load_cards_from_dir(os.path.join(base_dir, "personas"), PERSONA_CARDS, ".persona.yaml", "persona")
    _load_cards_from_dir(os.path.join(base_dir, "abilities"), ABILITY_CARDS, ".ability.yaml", "abilities")
    _load_cards_from_dir(os.path.join(base_dir, "engines"), ENGINE_CARDS, ".engine.yaml", "engine")
    
    print("[PROMPT_MGR] Card loading complete.")

# Load cards when this module is first imported by the server.
load_all_cards()
# --- END OF FILE prompt.py ---