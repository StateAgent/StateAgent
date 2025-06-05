import os
import sys
import yaml
import subprocess
from huggingface_hub import hf_hub_download, HfHubDownloadError

# --- Configuration ---
TARGET_GGUF_DIR = r"A:\LLM-Server\models\GGUF"
MODEL_REGISTRY_PATH = r"A:\LLM-Server\Llama\model_registry.yaml"
GENERATE_CONFIG_SCRIPT = r"A:\LLM-Server\generate_llama_swap_config.py"


def load_model_registry():
    """Load model registry entries."""
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


def pull_model_from_hf(repo_id: str, filename: str, tag_name: str, subfolder: str | None = None) -> bool:
    """Download a model from Hugging Face if it does not already exist."""
    print(f"\nAttempting to pull '{tag_name}' (file: '{filename}' from '{repo_id}')...")
    os.makedirs(TARGET_GGUF_DIR, exist_ok=True)
    local_model_path = os.path.join(TARGET_GGUF_DIR, filename)

    if os.path.exists(local_model_path):
        print(f"Model '{tag_name}' already exists locally at {local_model_path}. Skipping download.")
        return True

    try:
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            subfolder=subfolder,
            local_dir=TARGET_GGUF_DIR,
            local_dir_use_symlinks=False,
        )
        print(f"Successfully downloaded '{tag_name}' to: {local_model_path}")
        return True
    except HfHubDownloadError as e:
        print(f"Error pulling model '{tag_name}': {e}")
        print("Please check the model tag, repository ID, and filename in your model_registry.yaml.")
        print(f"Also verify if '{filename}' exists in the '{repo_id}' Hugging Face repository.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while pulling model '{tag_name}': {e}")
        return False


def update_config_after_pull() -> None:
    """Regenerate LlamaSwap's configuration after pulling a model."""
    print("\nModel pulled. Rebuilding LlamaSwap config.yaml to include new models...")
    try:
        subprocess.run([sys.executable, GENERATE_CONFIG_SCRIPT], check=True)
        print("LlamaSwap config.yaml successfully rebuilt.")
    except subprocess.CalledProcessError as e:
        print(f"Error rebuilding LlamaSwap config: {e}")
        print("You may need to manually run 'llama list -rebuild'.")
    except FileNotFoundError:
        print(f"Error: Config generation script not found at {GENERATE_CONFIG_SCRIPT}.")
        print("Please ensure your Python scripts are correctly placed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python llama_pull.py <model_tag>")
        print("Example: python llama_pull.py mistral:7b-instruct-q5")
        print("\nTo see available tags, check your model_registry.yaml or run 'llama list'.")
        sys.exit(1)

    model_tag_to_pull = sys.argv[1]
    registry_models = load_model_registry()

    for model_entry in registry_models:
        if model_entry["name"].lower() == model_tag_to_pull.lower():
            print(
                f"Found '{model_tag_to_pull}' in registry. Description: {model_entry.get('description', 'N/A')}"
            )
            success = pull_model_from_hf(
                model_entry["repo_id"],
                model_entry["filename"],
                model_entry["name"],
            )
            if success:
                update_config_after_pull()
            sys.exit(0)

    print(f"Error: Model tag '{model_tag_to_pull}' not found in {MODEL_REGISTRY_PATH}.")
    print("Please add it to the registry or check for typos.")
    print("Run 'llama list' to see models you can currently manage.")
    sys.exit(1)
