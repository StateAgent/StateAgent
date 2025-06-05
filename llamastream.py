import os
import requests
import numpy as np
from safetensors.numpy import save_file, load_file
from pathlib import Path
import time

VECTOR_DIM = 4096
MEMORY_DIR = Path('.prom_night_memories')
MEMORY_URL = 'http://localhost:8080/embed'
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def embed_with_llama(text: str) -> np.ndarray:
    """Call the local Llama embedding endpoint and return a vector."""
    response = requests.post(MEMORY_URL, json={'content': text})
    if response.status_code == 200:
        vec = np.array(response.json(), dtype=np.float32)
        return vec
    raise RuntimeError(f"Failed to embed: {response.text}")


def save_memory(vec: np.ndarray) -> str:
    """Persist a vector to disk using safetensors and return the timestamp tag."""
    ts = str(int(time.time() * 1000))
    filename = MEMORY_DIR / f"{ts}.safetensors"
    save_file({'embedding': vec}, filename)
    print(f"\u2693 Memory anchored: {filename}")
    return ts


def remember_this(text: str) -> str:
    """Embed the provided text and store the resulting vector."""
    vec = embed_with_llama(text)
    return save_memory(vec)


def load_memory(file: Path) -> np.ndarray:
    """Load a saved embedding from disk."""
    data = load_file(str(file))
    return data['embedding']


def list_memory_files() -> list[Path]:
    return sorted(MEMORY_DIR.glob('*.safetensors'))


def query_memory(text: str, top_k: int = 3):
    """Embed the query and return the filenames of the closest stored memories."""
    if top_k <= 0:
        return []
    query_vec = embed_with_llama(text)
    memories = []
    for file in list_memory_files():
        try:
            vec = load_memory(file)
            if vec.shape[0] != query_vec.shape[0]:
                continue
            score = float(np.dot(vec, query_vec))
            memories.append((score, file))
        except Exception:
            continue
    memories.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in memories[:top_k]]


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Simple Llama memory stream')
    sub = parser.add_subparsers(dest='cmd')

    remember = sub.add_parser('remember', help='Embed and store some text')
    remember.add_argument('text', help='Text to remember')

    recall = sub.add_parser('recall', help='Find similar memories for a query')
    recall.add_argument('query', help='Query text')
    recall.add_argument('--top', type=int, default=3, help='How many results to return')

    args = parser.parse_args()

    if args.cmd == 'remember':
        remember_this(args.text)
    elif args.cmd == 'recall':
        results = query_memory(args.query, args.top)
        if results:
            print('Top matches:')
            for p in results:
                print(p)
        else:
            print('No memories found.')
    else:
        parser.print_help()
