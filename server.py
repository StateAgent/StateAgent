# --- START OF REFACTORED server.py ---

import time, uuid, argparse, os, threading
from flask import Flask, request, jsonify, render_template  # <-- ADDED render_template
from flask_cors import CORS
import requests

import serverconfig, prompt
from agent_core import StateAgent
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Background Services ---
class PromptChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if any(event.src_path.endswith(ext) for ext in ['.persona.yaml', '.ability.yaml', '.engine.yaml']):
            print(f"[PROMPTS_WATCHER] Change detected. Reloading all cards..."); prompt.load_all_cards()

def start_prompt_watcher():
    path = serverconfig.PROMPTS_DIR
    os.makedirs(os.path.join(path, "personas"), exist_ok=True)
    os.makedirs(os.path.join(path, "abilities"), exist_ok=True)
    os.makedirs(os.path.join(path, "engines"), exist_ok=True)
    observer = Observer()
    observer.schedule(PromptChangeHandler(), path, recursive=True)
    observer.daemon = True
    observer.start()
    print(f"[PROMPTS_WATCHER] Watching for changes in: {path}")
    return observer

app = Flask(__name__)
CORS(app)
agent = None
LAST_KNOWN_MODEL = [None] 

def model_monitor_thread(stop_event):
    global LAST_KNOWN_MODEL; print("[MODEL_MONITOR] Starting...")
    while not stop_event.is_set():
        try:
            resp = requests.get(f"{serverconfig.LLAMA_CPP_BASE_URL}/v1/models", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("data", []); current_model = os.path.basename(models[0]['id']) if models else None
                if current_model and LAST_KNOWN_MODEL[0] != current_model:
                    print(f"[MODEL_MONITOR] !! MODEL ONLINE: {current_model} !!"); LAST_KNOWN_MODEL[0] = current_model
            elif LAST_KNOWN_MODEL[0] is not None:
                print(f"[MODEL_MONITOR] Model '{LAST_KNOWN_MODEL[0]}' offline."); LAST_KNOWN_MODEL[0] = None
        except:
            if LAST_KNOWN_MODEL[0] is not None: print("[MODEL_MONITOR] Llama.cpp unreachable."); LAST_KNOWN_MODEL[0] = None
        stop_event.wait(5)
    print("[MODEL_MONITOR] Stopped.")

def _get_models_list():
    try:
        resp = requests.get(f"{serverconfig.LLAMA_CPP_BASE_URL}/v1/models", timeout=10); resp.raise_for_status()
        return [{"id": os.path.basename(m.get("id")), "object": "model"} for m in resp.json().get("data", []) if m.get("id")]
    except: return []

# --- Routes (UI and API) ---

# NEW: Route to serve the main web page
@app.route('/')
def index():
    """Serves the main index.html file from the 'templates' folder."""
    return render_template('index.html')

@app.route('/v1/models', methods=['GET'])
@app.route('/models', methods=['GET'])
def list_models(): return jsonify({"object": "list", "data": _get_models_list()})

@app.route('/v1/embeddings', methods=['POST'])
def handle_embeddings():
    try:
        request_data = request.json
        if not request_data or "input" not in request_data:
            return jsonify({"error": "Invalid payload. 'input' key is required."}), 400
        user_input = request_data.get("input")
        if isinstance(user_input, str):
            payload_input = [user_input]
        elif isinstance(user_input, list):
            payload_input = user_input
        else:
            return jsonify({"error": "'input' must be a string or a list of strings."}), 400
        safe_payload = {"input": payload_input}
        headers = { "Content-Type": "application/json" }
        response = requests.post(serverconfig.LLAMA_CPP_RAW_EMBEDDING_URL, json=safe_payload, headers=headers, timeout=30)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.HTTPError as http_err:
        print(f"[EMBEDDING_PROXY_ERROR] HTTP Error: {http_err.response.status_code} - {http_err.response.text}")
        return jsonify({"error": "Failed to get embedding from backend."}), 500
    except Exception as e:
        print(f"[EMBEDDING_PROXY_ERROR] {e}")
        return jsonify({"error": "Failed to get embedding from backend."}), 500

@app.route('/v1/chat/completions', methods=['POST'])
@app.route('/chat/completions', methods=['POST'])
def chat_completions():
    if not agent: return jsonify({"error": "Agent not initialized."}), 500
    try:
        request_data = request.json
        if not request_data or "messages" not in request_data: return jsonify({"error": "Invalid JSON payload"}), 400
        model_id = request_data.get("model") or LAST_KNOWN_MODEL[0]
        if not model_id: discovered = _get_models_list(); model_id = discovered[0]['id'] if discovered else None
        if not model_id: return jsonify({"error": "No model is loaded in the backend."}), 503
        ai_response_text = agent.handle_request(request_data, model_id)
        return jsonify({"id": f"cmpl-{uuid.uuid4()}", "model": agent.current_model_id, "choices": [{"message": {"role": "assistant", "content": ai_response_text}}]})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Internal Server Error: {e}"}), 500

# --- Main Execution Block ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="State Agent Orchestrator v0.2")
    parser.add_argument('-p', '--persona', type=str.upper, default=serverconfig.DEFAULT_PERSONA_ID, help="Default Persona ID (e.g., AA).")
    parser.add_argument('-a', '--ability', type=str, default=serverconfig.DEFAULT_ABILITY_ID, help="Default Ability ID (e.g., 01).")
    parser.add_argument('-e', '--engine', type=str.upper, default=serverconfig.DEFAULT_ENGINE_ID, help="Default Engine ID (e.g., F0).")
    args = parser.parse_args()

    # ASCII Art and other startup messages...
    print(r"""...""") # (Keeping this brief to save space)

    agent = StateAgent(persona_id=args.persona, ability_id=args.ability, engine_id=args.engine)
    
    prompt_watcher = start_prompt_watcher()
    stop_monitor_event = threading.Event()
    model_monitor = threading.Thread(target=model_monitor_thread, args=(stop_monitor_event,))
    model_monitor.start()

    port = serverconfig.ORCHESTRATOR_PORT; host = serverconfig.HOST
    print(f"Orchestrator v0.2 starting on http://{host}:{port}")
    print(f"Web UI available at http://{host}:{port}") # Added a message for clarity
    try:
        app.run(host=host, port=port, debug=False, use_reloader=False)
    finally:
        print("[SERVER] Shutdown initiated..."); 
        if prompt_watcher: prompt_watcher.stop(); prompt_watcher.join()
        stop_monitor_event.set(); model_monitor.join()
        print("[SERVER] All background services stopped. Goodbye.")