import os
import yaml
import re

LLAMA_SWAP_CONFIG_PATH = r"A:\LLM-Server\Llama\config.yaml"
GGUF_MODELS_DIR = r"A:\LLM-Server\models\GGUF"
MODEL_REGISTRY_PATH = r"A:\LLM-Server\Llama\model_registry.yaml"


def get_file_size_h(filepath):
    """Return human-readable file size."""
    if not os.path.exists(filepath):
        return "N/A"
    size_bytes = os.path.getsize(filepath)
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024**2):.2f} MB"
    return f"{size_bytes / (1024**3):.2f} GB"


def parse_model_quant(filename):
    """Parse quantization string from filename."""
    match = re.search(r"\.(Q[0-9]_[A-Z]_?[A-Z]?|F[0-9]+|G[0-9]+)\.gguf$", filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return "Unknown"


def load_model_registry():
    try:
        with open(MODEL_REGISTRY_PATH, "r") as f:
            return yaml.safe_load(f).get("models", [])
    except FileNotFoundError:
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing model registry: {e}")
        return []


def list_configured_models():
    print("--- Local LlamaSwap Models ---")

    configured_models_info = {}
    try:
        with open(LLAMA_SWAP_CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        for model_entry in config.get("models", []):
            name = model_entry.get("name")
            cmd_str = model_entry.get("cmd", "")
            model_path = ""
            if "--model" in cmd_str.split():
                try:
                    idx = cmd_str.split().index("--model") + 1
                    model_path = cmd_str.split()[idx]
                except (ValueError, IndexError):
                    pass
            configured_models_info[name] = {"path": model_path, "cmd_args": cmd_str}
    except FileNotFoundError:
        print(f"Warning: LlamaSwap config not found at {LLAMA_SWAP_CONFIG_PATH}.")
        print("Run 'llama list -rebuild' to generate the config.")
        return
    except yaml.YAMLError as e:
        print(f"Error parsing LlamaSwap config: {e}")
        return

    registry_models = {entry["name"].lower(): entry for entry in load_model_registry()}

    if not configured_models_info:
        print("No models are currently configured in LlamaSwap's config.yaml.")
        return

    print(f"{'NAME':<25}{'SIZE':<10}{'QUANT':<8}{'MMPROJ':<8}{'DESCRIPTION':<30}")
    print("-" * 100)

    for name, info in configured_models_info.items():
        model_path = info["path"]
        base_filename = os.path.basename(model_path)
        file_size = get_file_size_h(model_path)
        quantization = parse_model_quant(base_filename)
        mmproj_support = "Yes" if "--mmproj" in info["cmd_args"] else "No"
        description = registry_models.get(name.lower(), {}).get("description", "N/A")

        print(f"{name:<25}{file_size:<10}{quantization:<8}{mmproj_support:<8}{description:<30}")

    print("-" * 100)


if __name__ == "__main__":
    list_configured_models()
