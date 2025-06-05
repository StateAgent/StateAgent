import os
import yaml

# --- Configuration ---
GGUF_MODELS_DIR = r"A:\LLM-Server\models\GGUF"
LLAMA_SWAP_CONFIG_OUTPUT = r"A:\LLM-Server\Llama\config.yaml"
LLAMA_SERVER_EXE = r"A:\LLM-Server\Llama\server\llama-server.exe"
MODEL_REGISTRY_PATH = r"A:\LLM-Server\Llama\model_registry.yaml"


def load_model_registry():
    """Load model metadata from the registry."""
    try:
        with open(MODEL_REGISTRY_PATH, "r") as f:
            return yaml.safe_load(f).get("models", [])
    except FileNotFoundError:
        print(f"Warning: Model registry not found at {MODEL_REGISTRY_PATH}. Models will be named by filename.")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing model registry: {e}")
        return []


def generate_config():
    """Generate a config.yaml file for LlamaSwap based on available GGUF files."""
    print("--- Generating LlamaSwap config.yaml ---")
    print(f"Scanning for GGUF models in: {GGUF_MODELS_DIR}")

    os.makedirs(os.path.dirname(LLAMA_SWAP_CONFIG_OUTPUT), exist_ok=True)

    models_list = []
    registry_models = load_model_registry()
    registry_map = {entry["filename"].lower(): entry["name"] for entry in registry_models}

    gguf_files = [f for f in os.listdir(GGUF_MODELS_DIR) if f.lower().endswith(".gguf")]
    if not gguf_files:
        print("No GGUF models found. The config file will be empty or contain only default settings.")

    for filename in gguf_files:
        full_path = os.path.join(GGUF_MODELS_DIR, filename)

        model_name = registry_map.get(filename.lower(), os.path.splitext(filename)[0])
        server_cmd = (
            f'"{LLAMA_SERVER_EXE}" --port ${{PORT}} --model "{full_path}" --n-gpu-layers 0'
        )

        for entry in registry_models:
            if entry["name"] == model_name and entry.get("server_args"):
                server_cmd += f" {entry['server_args']}"
                break

        models_list.append({"name": model_name, "cmd": server_cmd})

    config_data = {"port": 8002, "models": models_list}

    try:
        with open(LLAMA_SWAP_CONFIG_OUTPUT, "w") as f:
            yaml.dump(config_data, f, indent=2, sort_keys=False)
        print(f"LlamaSwap config.yaml generated successfully at: {LLAMA_SWAP_CONFIG_OUTPUT}")
    except Exception as e:
        print(f"Error writing config.yaml: {e}")


if __name__ == "__main__":
    generate_config()
