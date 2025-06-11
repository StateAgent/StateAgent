# agent/memory_manager.py
import os
import threading
import uuid
import numpy as np
import requests
from sklearn.metrics.pairwise import cosine_similarity
from collections import deque
import serverconfig

try:
    from safetensors.numpy import save_file, load_file
    VECTOR_FILE_EXTENSION = ".safetensors"
except ImportError:
    print("WARN: safetensors library not found. Using NumPy .npz for this session.")
    def save_file(data, filepath): np.savez(filepath, **data)
    def load_file(filepath): return np.load(filepath)
    VECTOR_FILE_EXTENSION = ".npz"

class WorkingMemory:
    """Handles the short-term conversation context."""
    def __init__(self):
        self.history = deque(maxlen=20)
    def add_message(self, role, content):
        self.history.append({"role": role, "content": content})
    def get_history(self):
        return list(self.history)
    def clear(self):
        self.history.clear()

class LongTermMemory:
    """Handles vector-based long-term memory storage and retrieval."""
    def __init__(self, vector_dir, log_file):
        self.vector_dir = vector_dir
        self.chat_log_file = log_file
        self.vectors = {}
        self.lock = threading.Lock()
        os.makedirs(self.vector_dir, exist_ok=True)
        if not os.path.exists(self.chat_log_file):
            with open(self.chat_log_file, "w", encoding="utf-8") as f:
                f.write("# State Agent Memory Log\n")
        threading.Thread(target=self._load_vectors_from_disk, daemon=True).start()

    def _load_vectors_from_disk(self):
        print(f"LTM: Loading existing memories from {self.vector_dir}")
        with self.lock:
            self.vectors = {}
            for filename in os.listdir(self.vector_dir):
                if filename.endswith(VECTOR_FILE_EXTENSION):
                    filepath = os.path.join(self.vector_dir, filename)
                    stem = os.path.splitext(filename)[0]
                    try:
                        data = load_file(filepath)
                        self.vectors[stem] = np.array(data["embedding"], dtype=np.float32)
                    except Exception as e:
                        print(f"LTM_WARN: Failed to load vector from {filepath}: {e}")
        print(f"LTM: Loaded {len(self.vectors)} memories.")

    def _get_embedding(self, text):
        try:
            response = requests.post(serverconfig.LLAMA_CPP_EMBEDDING_URL, json={"input": text})
            response.raise_for_status()
            return np.array(response.json()['data'][0]['embedding'], dtype=np.float32)
        except Exception as e:
            print(f"FATAL: Embedding call failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"SERVER_RESPONSE: {e.response.text}")
            raise

    def remember(self, text_to_remember):
        try:
            print(f"  [WORKER] Thread started. Processing memory: '{text_to_remember[:60]}...'")
            vec = self._get_embedding(text_to_remember)
            print(f"  [WORKER] Embedding received.")
            unique_id = str(uuid.uuid4())
            filepath = os.path.join(self.vector_dir, f"{unique_id}{VECTOR_FILE_EXTENSION}")
            with self.lock:
                print(f"  [WORKER] Saving vector to disk: {filepath}")
                save_file({"embedding": vec}, filepath)
                self.vectors[unique_id] = vec
                clean_text = text_to_remember.replace('\n', ' ').strip()
                with open(self.chat_log_file, "a", encoding="utf-8") as f:
                    f.write(f"{unique_id}|{clean_text}\n")
            print(f"  [WORKER] >>> Memory anchor complete for {unique_id}. Thread finished. <<<")
        except Exception as e:
            print(f"  [WORKER_ERROR] Failed to save memory: {e}")

    def recall(self, query_text, top_k=3, similarity_threshold=0.5):
        if not self.vectors: return []
        with self.lock:
            stems = list(self.vectors.keys())
            vecs = np.array(list(self.vectors.values()))
            if len(stems) == 0: return []
        try:
            query_vec = self._get_embedding(query_text)
            similarities = cosine_similarity([query_vec], vecs)[0]
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            recalled_texts = []
            log_data = {}
            with open(self.chat_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if "|" in line:
                        stem, text = line.strip().split("|", 1)
                        log_data[stem] = text
            for i in top_indices:
                if similarities[i] >= similarity_threshold:
                    if (stem_to_find := stems[i]) in log_data:
                        recalled_texts.append(log_data[stem_to_find])
            return recalled_texts
        except Exception as e:
            print(f"ERROR: Failed during memory recall: {e}")
            return []