import os
import sys
import yaml
import subprocess

# --- Configuration ---
GGUF_MODELS_DIR = r"A:\LLM-Server\models\GGUF"
MODEL_REGISTRY_PATH = r"A:\LLM-Server\Llama\model_registry.yaml"
LLAMA_SWAP_CONFIG_PATH = r"A:\LLM-Server\Llama\config.yaml"
GENERATE_CONFIG_SCRIPT = r"A:\LLM-Server\generate_llama_swap_config.py"


def load_model_registry():
    """Load the model registry."""
    try:
        with open(MODEL_REGISTRY_PATH, "r") as f:
            return yaml.safe_load(f).get("models", [])
    except FileNotFoundError:
        print(f"Warning: Model registry not found at {MODEL_REGISTRY_PATH}. Please create it in A:\\LLM-Server\\Llama\\.")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing model registry: {e}")
        return []


def update_config_after_removal(removed_model_filename: str) -> None:
    """Remove the model from config.yaml and regenerate if necessary."""
    print("Updating LlamaSwap config.yaml after model removal...")
    try:
        with open(LLAMA_SWAP_CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)

        updated_models = []
        removed = False
        for model_entry in config.get("models", []):
            cmd_str = model_entry.get("cmd", "")
            if removed_model_filename not in cmd_str:
                updated_models.append(model_entry)
            else:
                removed = True

        if removed:
            config["models"] = updated_models
            with open(LLAMA_SWAP_CONFIG_PATH, "w") as f:
                yaml.dump(config, f, indent=2, sort_keys=False)
            print("Model successfully removed from config.yaml.")
        else:
            print("Model was not found in config.yaml, running full rebuild.")
            subprocess.run([sys.executable, GENERATE_CONFIG_SCRIPT], check=True)
            print("LlamaSwap config.yaml rebuilt.")
    except (FileNotFoundError, yaml.YAMLError, subprocess.CalledProcessError) as e:
        print(f"Error updating/rebuilding LlamaSwap config: {e}")
        print("You may need to manually run 'llama list -rebuild' to resync your config.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python llama_rm.py <model_tag>")
        print("Example: python llama_rm.py mistral:7b-instruct-q5")
        sys.exit(1)

    model_tag_to_remove = sys.argv[1]
    registry_models = load_model_registry()

    model_info = None
    for entry in registry_models:
        if entry["name"].lower() == model_tag_to_remove.lower():
            model_info = entry
            break

    if not model_info:
        print(f"Error: Model tag '{model_tag_to_remove}' not found in {MODEL_REGISTRY_PATH}.")
        print("Cannot remove. Check your model_registry.yaml or run 'llama list'.")
        sys.exit(1)

    filename_to_remove = model_info["filename"]
    full_path_to_remove = os.path.join(GGUF_MODELS_DIR, filename_to_remove)

    print(f"\nAttempting to remove model '{model_tag_to_remove}' (file: {full_path_to_remove})...")

    if not os.path.exists(full_path_to_remove):
        print(f"Model file not found at {full_path_to_remove}. It might already be removed.")
        update_config_after_removal(filename_to_remove)
        sys.exit(0)

    try:
        os.remove(full_path_to_remove)
        print(f"Successfully removed model file: {full_path_to_remove}")
        update_config_after_removal(filename_to_remove)
        sys.exit(0)
    except OSError as e:
        print(f"Error removing file {full_path_to_remove}: {e}")
        print("Please ensure you have permissions and the file is not in use.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
