# remind.py

import os
import numpy as np
from pathlib import Path
from safetensors.numpy import load_file
from sklearn.metrics.pairwise import cosine_similarity

# Folder containing all memory embeddings
VECTOR_DIR = Path("vectors")
CHAT_LOG = "chat_logs.txt"

def load_all_vectors():
    """
    Load all .safetensors files into RAM at startup
    Returns: dict of {filename_stem: embedding_vector}
    """
    vectors = {}
    for file in VECTOR_DIR.glob("*.safetensors"):
        try:
            data = load_file(file)
            vec = data["embedding"].astype(np.float32)  # Ensure float32
            vectors[file.stem] = vec  # key = memory0001, etc.
        except Exception as e:
            print(f"⚠️ Failed to load {file}: {e}")
    print(f"🧠 Loaded {len(vectors)} memories into RAM")
    return vectors

def find_closest(query_vec, vectors, top_k=5):
    """
    Brute-force cosine similarity over RAM-loaded vectors
    """
    results = []
    query_vec = query_vec.astype(np.float32)
    for name, vec in vectors.items():
        sim = cosine_similarity([query_vec], [vec])[0][0]
        results.append((name, sim))
    return sorted(results, key=lambda x: -x[1])[:top_k]

def lookup_log(timestamp):
    """
    Find matching chat log line by timestamp
    Format: 1712345678|User: Who are you?
    """
    try:
        with open(CHAT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(f"{timestamp}|"):
                    return line.strip()
    except FileNotFoundError:
        return None
    return None

if __name__ == "__main__":
    # Load all vectors into RAM once
    memories = load_all_vectors()

    if not memories:
        print("💀 No memories found. The mind is empty.")
        exit()

    # Example query: use one of the loaded vectors as query
    sample_query = next(iter(memories.values()))  # First vector as test query

    # Search for closest matches
    matches = find_closest(sample_query, memories)

    # Print results
    print("\n🔍 Top Matches:")
    for ts, score in matches:
        log_entry = lookup_log(ts)
        print(f"{ts} | {log_entry} | Score: {score:.4f}")