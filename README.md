# Station

This repository collects helper scripts for managing GGUF models with [LlamaSwap](https://github.com/infinyte7/llama-swap) and mimicking a lightweight Ollama workflow.  
The scripts live in the `llama_tools` directory and include utilities to pull, list, remove and run local models.

## Scripts

- `generate_llama_swap_config.py` – Scans your GGUF directory and rebuilds the `config.yaml` used by LlamaSwap.
- `llama_list.py` – Lists models currently configured in `config.yaml` and displays information from `model_registry.yaml`.
- `llama_pull.py` – Downloads a model from HuggingFace based on an entry in `model_registry.yaml` and regenerates the config.
- `llama_rm.py` – Removes a model from disk and updates the config.
- `llama_run.py` – Launches a temporary `llama-server` and `llama-chat` session for a given model tag. If the model isn't downloaded it will attempt to pull it automatically.
- `llamastream.py` – Simple memory helper that talks to a running Llama embed API on `localhost:8080` and stores embeddings as `.safetensors` files. It can also query the stored vectors to find related memories.

All file paths in these scripts point to `A:\LLM-Server\...` by default. Adjust them to suit your environment.

The repository currently does not include the actual models or configuration files. Refer to your existing `model_registry.yaml` and LlamaSwap installation to make full use of these tools.
