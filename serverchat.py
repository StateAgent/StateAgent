# --- START OF FILE serverchat.py ---

import requests, json, os, argparse, serverconfig

# Session ID will be given by the server on the first request
SESSION_ID = None

def send_request(payload):
    """Handles sending requests and printing/managing session responses."""
    global SESSION_ID

    if SESSION_ID:
        payload['session_id'] = SESSION_ID
        
    try:
        response = requests.post(
            f"http://{serverconfig.HOST}:{serverconfig.ORCHESTRATOR_PORT}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        response.raise_for_status()
        json_response = response.json()
        
        # Capture the session_id from the server's response
        if 'session_id' in json_response and SESSION_ID is None:
            SESSION_ID = json_response['session_id']
            print(f"\n[CLIENT] Session started. Your permanent Session ID for this chat is: {SESSION_ID}\n")
        
        reply = json_response.get('choices', [{}])[0].get('message', {}).get('content', 'Error: No response content.')
        print(f"AI> {reply}")

    except requests.exceptions.RequestException:
        print(f"\nERROR: Could not connect to the server at http://{serverconfig.HOST}:{serverconfig.ORCHESTRATOR_PORT}. Is it running?")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == '__main__':
    
    print("\n--- Sovereign Client v0.2 ---")
    print(f"[*] Orchestrator Target: http://{serverconfig.HOST}:{serverconfig.ORCHESTRATOR_PORT}")
    print("\n--- Wizard's Control Panel ---")
    print("  //user <name>       - Switch the active user dossier (e.g., //user Scott)")
    print("  //persona <id>      - Change the current user's persona (e.g., //persona AA)")
    print("  //ability <id>      - Change the current user's abilities (e.g., //ability 00)")
    print("  //engine <id>       - Change the current user's thinking style (e.g., //engine F0)")
    print("  //loadout <id>      - Apply a preset mind from config.ini (e.g., //loadout TEST99)")
    print("-----------------------------------")
    
    while True:
        # We don't need to know the user here; the server manages it via `//user` command
        user_input = input("You> ")
        if not user_input: continue
        if user_input.lower() in ['exit', 'quit']: break
        
        payload = {
            "messages": [{"role": "user", "content": user_input}]
            # No 'user' field is needed; we use the //user command to manage state.
        }
        send_request(payload)

    print("\n--- Client Disconnected ---")

# --- END OF FILE serverchat.py ---