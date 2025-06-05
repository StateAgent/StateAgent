import os
import sys
import yaml
import subprocess
import time
import socket
import shlex

LLAMA_SWAP_CONFIG_PATH = r"A:\LLM-Server\Llama\config.yaml"
LLAMA_SERVER_EXE_PATH = r"A:\LLM-Server\Llama\server\llama-server.exe"
LLAMA_CHAT_EXE_PATH = r"A:\LLM-Server\Llama\server\llama-chat.exe"
MODEL_REGISTRY_PATH = r"A:\LLM-Server\Llama\model_registry.yaml"
PULL_SCRIPT_PATH = r"A:\LLM-Server\llama_pull.py"
TARGET_GGUF_DIR = r"A:\LLM-Server\models\GGUF"

BASE_SERVER_PORT = 8090


def find_free_port(start_port: int) -> int:
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found for temporary server!")


def load_model_registry():
    try:
        with open(MODEL_REGISTRY_PATH, "r") as f:
            return yaml.safe_load(f).get("models", [])
    except FileNotFoundError:
        print(
            f"Warning: Model registry not found at {MODEL_REGISTRY_PATH}. Please create it in A:\\LLM-Server\\Llama\\."
        )
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing model registry: {e}")
        return []


def get_model_info_from_config(model_name: str):
    """Retrieve model path and base server arguments from LlamaSwap config."""
    try:
        with open(LLAMA_SWAP_CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        for model_entry in config.get("models", []):
            if model_entry.get("name") == model_name:
                cmd_template = model_entry.get("cmd")
                if not cmd_template:
                    return None, None
                server_args = []
                model_path = None
                parts = shlex.split(cmd_template)
                i = 0
                while i < len(parts):
                    part = parts[i]
                    if part.lower() == LLAMA_SERVER_EXE_PATH.lower():
                        i += 1
                        continue
                    if part == "--port" and i + 1 < len(parts) and parts[i + 1] == "${PORT}":
                        i += 2
                        continue
                    if part == "--model" and i + 1 < len(parts):
                        model_path = parts[i + 1]
                        server_args.extend([part, parts[i + 1]])
                        i += 2
                        continue
                    server_args.append(part)
                    i += 1
                return model_path, server_args
    except FileNotFoundError:
        return None, None
    except yaml.YAMLError as e:
        print(f"Error parsing LlamaSwap config: {e}")
        return None, None
    return None, None


def run_interactive_model(model_tag: str) -> None:
    print(f"Attempting to run interactive session for model: {model_tag}")

    registry_models = load_model_registry()
    model_info = next((m for m in registry_models if m["name"].lower() == model_tag.lower()), None)
    if not model_info:
        print(f"Error: Model tag '{model_tag}' not found in {MODEL_REGISTRY_PATH}.")
        print("Please add it to the registry or check for typos.")
        sys.exit(1)

    expected_path = os.path.join(TARGET_GGUF_DIR, model_info["filename"])
    if not os.path.exists(expected_path):
        print(f"Model '{model_tag}' not found locally at {expected_path}.")
        print("Attempting to pull model now...")
        try:
            pull_cmd = [sys.executable, PULL_SCRIPT_PATH, model_tag]
            subprocess.run(pull_cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to pull model: {e}")
            sys.exit(1)
        except FileNotFoundError:
            print(f"Pull script not found at {PULL_SCRIPT_PATH}.")
            sys.exit(1)
    else:
        print(f"Model '{model_tag}' found locally at {expected_path}.")

    model_path, base_args = get_model_info_from_config(model_tag)
    if not model_path or base_args is None:
        print("Model not properly configured in LlamaSwap config. Run 'llama list -rebuild'.")
        sys.exit(1)

    extra_args = shlex.split(model_info.get("server_args", ""))

    try:
        server_port = find_free_port(BASE_SERVER_PORT)
    except Exception as e:
        print(f"Error finding free port: {e}")
        sys.exit(1)

    server_cmd = [LLAMA_SERVER_EXE_PATH] + base_args + extra_args + ["--port", str(server_port)]
    print(f"\nLaunching temporary llama-server: {' '.join(server_cmd)}")

    server_process = None
    try:
        creationflags = (
            subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
        )
        server_process = subprocess.Popen(server_cmd, creationflags=creationflags, close_fds=True)
        print(f"llama-server started with PID: {server_process.pid}")
        print("Giving server 5 seconds to initialize...")
        time.sleep(5)

        chat_cmd = [LLAMA_CHAT_EXE_PATH, "--host", "127.0.0.1", "--port", str(server_port)]
        print(f"\nLaunching llama-chat: {' '.join(chat_cmd)}")
        print("Type 'exit' or 'quit' in the chat window to end the session.")
        chat_process = subprocess.run(chat_cmd)
        print(f"\nllama-chat exited with code: {chat_process.returncode}")
    except FileNotFoundError:
        print(
            f"Error: Could not find '{LLAMA_SERVER_EXE_PATH}' or '{LLAMA_CHAT_EXE_PATH}'. Please ensure they exist."
        )
    except Exception as e:
        print(f"An error occurred during process launch: {e}")
    finally:
        if server_process and server_process.poll() is None:
            print(f"Terminating llama-server (PID: {server_process.pid})...")
            try:
                if sys.platform == "win32":
                    subprocess.run(f"taskkill /F /PID {server_process.pid}", shell=True)
                else:
                    server_process.terminate()
                    server_process.wait(timeout=5)
                    if server_process.poll() is None:
                        server_process.kill()
                print("Server process terminated.")
            except Exception as e:
                print(f"Error terminating server process: {e}")
        else:
            print("llama-server process was already stopped or not started.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python llama_run.py <model_tag>")
        sys.exit(1)

    run_interactive_model(sys.argv[1])
