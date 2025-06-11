# serverconfig.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_DIR = os.path.join(BASE_DIR, "Memory")
CHAT_LOG_FILE = os.path.join(VECTOR_DIR, "chat_logs.txt")
ORCHESTRATOR_PORT = 8000
LLAMA_CPP_PORT = 8001
MODEL_ID = "state-agent-qwen-omni" # Renamed for clarity
LLAMA_CPP_CHAT_URL = f"http://127.0.0.1:{LLAMA_CPP_PORT}/v1/chat/completions"
LLAMA_CPP_EMBEDDING_URL = f"http://127.0.0.1:{LLAMA_CPP_PORT}/v1/embeddings"
YOUR_SERVER_URL = f"http://127.0.0.1:{ORCHESTRATOR_PORT}/v1/chat/completions"