# remember.py

import requests
import numpy as np
from safetensors.numpy import save_file
from pathlib import Path
import time
import os

# Root path for long-term memory storage
ROOT_PATH = r"A:\Station\Memory"
os.makedirs(ROOT_PATH, exist_ok=True)

# Directory for current session memories (optional temp buffer)
MEMORY_DIR = Path(".prom_night_memories")
os.makedirs(MEMORY_DIR, exist_ok=True)

# Llama.cpp embedding endpoint
MEMORY_URL = "http://localhost:8080/embed"

def embed_with_llama(text):
    """
    Send text to llama.cpp embedding server
    Returns: embedding vector (np.float32)
    """
    response = requests.post(MEMORY_URL, json={"content": text})
    if response.status_code == 200:
        vec = np.array(response.json(), dtype=np.float32)
        return vec
    else:
        raise Exception(f"🔥 Embedding failed: {response.text}")

def get_next_memory_path(base_dir):
    """
    Generate auto-incremented filename like memory0001.safetensors
    """
    counter = 1
    while True:
        filename = f"memory{counter:04d}.safetensors"
        full_path = os.path.join(base_dir, filename)
        if not os.path.exists(full_path):
            return full_path
        counter += 1

def save_memory(vec, base_dir=ROOT_PATH, text=None):
    """
    Save embedding to auto-incremented .safetensors file
    """
    filepath = get_next_memory_path(base_dir)
    save_file({"embedding": vec}, filepath)
    print(f"🧠 Memory anchored: {filepath}")
    return filepath

def remember_this(text, compress=False):
    """
    Embed + save a new memory
    """
    vec = embed_with_llama(text)

    # Optional compression (disabled by default)
    if compress:
        vec = vec.astype(np.float16)  # Half-precision (saves space, loses some precision)

    return save_memory(vec, base_dir=ROOT_PATH)