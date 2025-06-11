# server.py
# API Gateway for the State Agent. Handles HTTP requests.

import time
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from waitress import serve

import serverconfig
from agent.agent_core import StateAgent # <-- Note the new import path

# --- FLASK APPLICATION SETUP ---
app = Flask(__name__)
CORS(app)

# Create one global instance of our agent
agent = StateAgent()

# --- API ENDPOINTS ---

@app.route('/v1/models', methods=['GET'])
def list_models():
    """This endpoint tells clients like Open WebUI what model is available."""
    print("[API] /v1/models endpoint hit")
    model_data = {
        "object": "list",
        "data": [
            {
                "id": serverconfig.MODEL_ID,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "user"
            }
        ]
    }
    return jsonify(model_data)

@app.route('/v1/models/<path:model_id>', methods=['GET'])
def get_model_details(model_id):
    """Provides details for a specific model ID."""
    print(f"[API] /v1/models/{model_id} endpoint hit")
    if model_id == serverconfig.MODEL_ID:
        return jsonify({
            "id": serverconfig.MODEL_ID,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "user"
        })
    else:
        return jsonify({"error": {"message": f"The model '{model_id}' does not exist.", "type": "invalid_request_error", "code": "model_not_found"}}), 404

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """The main chat endpoint. It passes the request to the agent and returns the response."""
    request_data = request.json
    
    # Let the agent orchestrate the entire process
    ai_response_text = agent.handle_request(request_data)
    
    # Format the final response in the standard OpenAI format
    response_payload = {
        "id": f"chatcmpl-stateagent-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": serverconfig.MODEL_ID,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": ai_response_text}, "finish_reason": "stop"}]
    }
    return jsonify(response_payload)

if __name__ == '__main__':
    print("--- STATE AGENT SERVER (API Gateway) ---")
    print(f"INFO: Orchestrator starting on http://127.0.0.1:{serverconfig.ORCHESTRATOR_PORT}")
    print("INFO: Ready to receive requests from clients.")
    serve(app, host='0.0.0.0', port=serverconfig.ORCHESTRATOR_PORT, threads=8)