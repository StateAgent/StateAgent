# --- START OF REFACTORED serverconfig.py ---

import os
import configparser

CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'config.ini')

# --- Self-Healing Logic (Unchanged) ---
if not os.path.exists(CONFIG_FILE_PATH):
    print(f"INFO: No config.ini found. Creating a default file at: {CONFIG_FILE_PATH}")
    default_config = configparser.ConfigParser()
    default_config['server_settings'] = {'host': '127.0.0.1', 'port': '8000', 'llama_cpp_port': '8001'}
    # MODIFIED: Added initial_user to default config
    default_config['agent_defaults'] = {'persona': 'AA', 'ability': '01', 'engine': 'F0', 'initial_user': 'agent_memory'}
    default_config['loadouts'] = {'TEST99': 'AA,99,F0'}
    with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
        default_config.write(f)
    print("INFO: Default config.ini has been created successfully.")

config = configparser.ConfigParser()
config.read(CONFIG_FILE_PATH)

# --- Expose Config Settings (Updated for new keys) ---
try:
    HOST = config.get('server_settings', 'host')
    ORCHESTRATOR_PORT = config.getint('server_settings', 'port')
    LLAMA_CPP_PORT = config.getint('server_settings', 'llama_cpp_port')
    DEFAULT_PERSONA_ID = config.get('agent_defaults', 'persona').upper()
    DEFAULT_ABILITY_ID = config.get('agent_defaults', 'ability')
    DEFAULT_ENGINE_ID = config.get('agent_defaults', 'engine').upper()
    LOADOUTS = {k.upper(): v.split(',') for k, v in config.items('loadouts')} if config.has_section('loadouts') else {}
    # NEW: The name for the agent's main memory, falling back to 'agent_memory'
    INITIAL_USER_ID = config.get('agent_defaults', 'initial_user', fallback='agent_memory')
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    raise RuntimeError(f"FATAL: config.ini is missing a required section or key. Error: {e}")

# --- Derived Paths & URLs (Updated for new memory structure) ---
ORCHESTRATOR_BASE_URL = f"http://{HOST}:{ORCHESTRATOR_PORT}"
LLAMA_CPP_BASE_URL = f"http://{HOST}:{LLAMA_CPP_PORT}"
LLAMA_CPP_CHAT_URL = f"{LLAMA_CPP_BASE_URL}/v1/chat/completions"
LLAMA_CPP_RAW_EMBEDDING_URL = f"{LLAMA_CPP_BASE_URL}/v1/embeddings"
LLAMA_CPP_EMBEDDING_URL = f"{ORCHESTRATOR_BASE_URL}/v1/embeddings"

# --- NEW MEMORY PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")

# The folder for individual user/entity manifests
DOSSIER_DIR = os.path.join(MEMORY_DIR, "dossiers")

# The folder for the central, unified memory database
AGENT_MEMORY_PATH = os.path.join(MEMORY_DIR, INITIAL_USER_ID)
AGENT_VECTOR_DB_PATH = os.path.join(AGENT_MEMORY_PATH, "vectors")
MASTER_MEMORY_LOG_PATH = os.path.join(AGENT_MEMORY_PATH, "master_memory_log.csv")
SIGNATURES_FILE_PATH = os.path.join(AGENT_MEMORY_PATH, "signatures.safetensors")

# --- END OF REFACTORED serverconfig.py ---