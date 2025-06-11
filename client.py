# client.py
# A terminal client capable of sending text and media files.

import requests
import json
import base64
import os
import serverconfig

ORCHESTRATOR_URL = serverconfig.YOUR_SERVER_URL
USER_ID = "Scott"

print("--- State Agent Client ---")
print(f"[*] Connecting to: {ORCHESTRATOR_URL}")
print(f"[*] User: {USER_ID}")
print("[*] Commands: //mem [text], //see [path] [prompt], //hear [path] [prompt], exit")
print("-" * 35)

def send_request(payload):
    """Handles sending requests and printing responses."""
    try:
        response = requests.post(
            ORCHESTRATOR_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=240
        )
        response.raise_for_status()
        reply = response.json().get('choices', [{}])[0].get('message', {}).get('content', 'No response content.')
        print(f"AI> {reply}")
    except requests.exceptions.RequestException as e:
        print(f"\nERROR: Could not connect to the server at {ORCHESTRATOR_URL}. Is it running?")
        print(f"Details: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

while True:
    user_input = input(f"{USER_ID}> ")
    if not user_input:
        continue
    if user_input.lower() in ['exit', 'quit']:
        break

    command = user_input.split(" ", 1)[0].lower()
    
    if command in ["//see", "//hear"]:
        parts = user_input.split(" ", 2)
        if len(parts) < 2:
            print(f"Usage: {command} <path_to_file> [optional: question]")
            continue

        file_path = parts[1].strip().strip('"')
        question = parts[2] if len(parts) > 2 else ("What do you see in this image?" if command == "//see" else "Transcribe this audio.")

        if not os.path.exists(file_path):
            print(f"ERROR: File not found at '{file_path}'")
            continue
        
        print(f"Reading file: {file_path}")
        with open(file_path, "rb") as media_file:
            b64_data = base64.b64encode(media_file.read()).decode('utf-8')
        
        payload = {
            "messages": [{"role": "user", "content": question}],
            "image_data": b64_data
        }
        send_request(payload)
    else:
        payload = {"messages": [{"role": "user", "content": user_input}]}
        send_request(payload)

print("\n--- Client Disconnected ---")