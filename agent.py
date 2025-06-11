# agent/agent_core.py
import threading
import requests
import serverconfig
from .memory_manager import WorkingMemory, LongTermMemory

class StateAgent:
    def __init__(self):
        print("Initializing State Agent Core...")
        self.working_memory = WorkingMemory()
        self.long_term_memory = LongTermMemory(serverconfig.VECTOR_DIR, serverconfig.CHAT_LOG_FILE)
        self.lock = threading.Lock()
        print("State Agent Core Initialized.")

    def handle_request(self, request_data):
        with self.lock:
            # Extract main content and media data from the incoming request
            user_message_list = request_data.get('messages', [])
            if not user_message_list:
                return "Error: Invalid request, no messages found."
            
            user_content_text = user_message_list[-1].get('content', '')
            image_data_b64 = request_data.get('image_data')

            # --- Node 1: Command Parser ---
            if user_content_text.strip().lower().startswith("//mem "):
                payload_text = user_content_text.split(" ", 1)[1].strip()
                print(f"[AGENT] Intercepted //mem command. Anchoring: '{payload_text[:50]}...'")
                # Offload to a background thread so the UI isn't blocked
                threading.Thread(target=self.long_term_memory.remember, args=(payload_text,)).start()
                return "ACK: Memory anchor command received. Processing in the background."

            # --- Node 2: Memory Recall ---
            print(f"[AGENT] User query: '{user_content_text}'")
            recalled_memories = self.long_term_memory.recall(user_content_text)
            
            # --- Node 3: Prompt Formatter ---
            messages_to_send = self._build_llm_payload(user_content_text, image_data_b64, recalled_memories)
            
            # --- Node 4: LLM Call ---
            ai_response_text = self._call_llm(messages_to_send)
            
            # --- Node 5: Update Working Memory ---
            self.working_memory.add_message("user", user_content_text)
            self.working_memory.add_message("assistant", ai_response_text)
            
            return ai_response_text

    def _build_llm_payload(self, user_text, image_b64, recalled_memories):
        """Builds the complete message list for the LLM API call."""
        messages = [{"role": "system", "content": "You are a helpful AI assistant."}]
        
        if recalled_memories:
            recalled_str = "\n".join(f"- {mem}" for mem in recalled_memories)
            messages.append({"role": "system", "content": f"Relevant context from past conversations:\n{recalled_str}"})

        messages.extend(self.working_memory.get_history())
        
        # Build the current user's message (text or multimodal)
        current_user_content = []
        if image_b64:
            print("[AGENT] Attaching image data to the request.")
            current_user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
            })
        
        current_user_content.append({"type": "text", "text": user_text})
        messages.append({"role": "user", "content": current_user_content})
        
        return messages

    def _call_llm(self, messages):
        """Sends the payload to the Llama.cpp server and returns the response."""
        llama_payload = {
            "model": serverconfig.MODEL_ID,
            "messages": messages,
            "max_tokens": 1024,
            "stream": False
        }
        
        print("[AGENT] Sending OpenAI-style payload to Llama.cpp...")
        try:
            response = requests.post(
                serverconfig.LLAMA_CPP_CHAT_URL,
                json=llama_payload,
                headers={'Content-Type': 'application/json'},
                timeout=180
            )
            response.raise_for_status()
            ai_response_text = response.json()['choices'][0]['message']['content'].strip()
            print("[AGENT] Received successful response from Llama.cpp.")
            return ai_response_text
        except requests.exceptions.RequestException as e:
            error_msg = f"FATAL: Error communicating with Llama.cpp server: {e}"
            print(error_msg)
            if e.response is not None:
                print(f"  SERVER_RESPONSE_CODE: {e.response.status_code}")
                print(f"  SERVER_RESPONSE_BODY: {e.response.text}")
            return "Sorry, I encountered a communication error with my core intelligence."