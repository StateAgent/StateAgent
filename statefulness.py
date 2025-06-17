import os
import threading
import uuid
import numpy as np
import requests
import serverconfig
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from collections import deque

try:
    from safetensors.numpy import save_file, load_file
    VECTOR_FILE_EXTENSION = ".safetensors"
except ImportError:
    print("WARN: safetensors library not found. Using NumPy .npz for this session.")
    def save_file(data, filepath): np.savez(filepath, **data)
    def load_file(filepath): return np.load(filepath)
    VECTOR_FILE_EXTENSION = ".npz"

class UserDossier:
    def __init__(self, user_id):
        self.user_id = user_id
        ### MODIFIED ###
        # This class is now simplified. The complex file path logic is handled by the MemorySystem,
        # which is a cleaner separation of concerns. This class now just holds the agent's
        # state for a given user session.
        self.working_memory = deque(maxlen=20)
        self.persona_id = ""
        self.ability_id = ""
        self.engine_id = ""

    def add_message(self, role, content): self.working_memory.append({"role": role, "content": content})
    def get_history(self): return list(self.working_memory)

class MemorySystem:
    def __init__(self):
        self.lock = threading.Lock()
        os.makedirs(serverconfig.AGENT_VECTOR_DB_PATH, exist_ok=True)
        os.makedirs(serverconfig.DOSSIER_DIR, exist_ok=True)
        self.vectors = self._load_all_vectors()
        
        ### MODIFIED: Added 'speaker_id' to solve the "Two Sarahs" problem ###
        # This is the single most important data model change.
        try:
            self.master_log = pd.read_csv(serverconfig.MASTER_MEMORY_LOG_PATH)
        except FileNotFoundError:
            self.master_log = pd.DataFrame(columns=['uuid', 'timestamp', 'speaker_id', 'entity_id', 'text'])

        try:
            self.signatures = load_file(serverconfig.SIGNATURES_FILE_PATH)
        except FileNotFoundError: self.signatures = {}
        print(f"MemorySystem Initialized: {len(self.vectors)} vectors, {len(self.master_log)} log entries, {len(self.signatures)} user signatures.")

    def _load_all_vectors(self):
        vectors = {}
        for filename in os.listdir(serverconfig.AGENT_VECTOR_DB_PATH):
            if filename.endswith(VECTOR_FILE_EXTENSION):
                try: vectors[os.path.splitext(filename)[0]] = load_file(os.path.join(serverconfig.AGENT_VECTOR_DB_PATH, filename))["embedding"]
                except Exception as e: print(f"LTM_WARN: Failed to load vector '{filename}': {e}")
        return vectors

    def _get_embedding(self, text):
        resp = requests.post(serverconfig.LLAMA_CPP_EMBEDDING_URL, json={"input": [text]}, timeout=30); resp.raise_for_status()
        return np.array(resp.json()['data'][0]['embedding'], dtype=np.float32)

    ### MODIFIED: 'remember' now tracks the speaker ###
    def remember(self, speaker_id, entity_id, enriched_text):
        try:
            vec = self._get_embedding(enriched_text); unique_id = str(uuid.uuid4())
            with self.lock:
                vector_filepath = os.path.join(serverconfig.AGENT_VECTOR_DB_PATH, f"{unique_id}{VECTOR_FILE_EXTENSION}")
                save_file({"embedding": vec}, vector_filepath); self.vectors[unique_id] = vec
                
                new_entry_df = pd.DataFrame([{'uuid': unique_id, 'timestamp': pd.Timestamp.now(), 'speaker_id': speaker_id, 'entity_id': entity_id, 'text': enriched_text}])
                
                ### NEW: Fix for Pandas FutureWarning ###
                if self.master_log.empty:
                    self.master_log = new_entry_df
                else:
                    self.master_log = pd.concat([self.master_log, new_entry_df], ignore_index=True)

                self.master_log.to_csv(serverconfig.MASTER_MEMORY_LOG_PATH, index=False)
                
                # We still create dossier manifests for easy data management, but they are not the primary source for recall.
                entity_dossier_dir = os.path.join(serverconfig.DOSSIER_DIR, entity_id)
                os.makedirs(entity_dossier_dir, exist_ok=True)
                dossier_manifest_path = os.path.join(entity_dossier_dir, "memory_manifest.txt")
                with open(dossier_manifest_path, "a", encoding="utf-8") as f: f.write(f"{unique_id}\n")
            print(f"LTM: Memory anchor complete for entity '{entity_id}' spoken by '{speaker_id}': {unique_id}")
        except Exception as e: print(f"LTM_ERROR: Failed to save memory for entity '{entity_id}': {e}")

    ### DELETED: The old 'recall' function ###
    # It has been replaced by the more powerful 'intelligent_recall'.

    ### NEW: Helper method for intelligent recall ###
    def _extract_entities_from_query(self, query):
        """Uses the LLM to find what subjects the user is asking about."""
        entity_prompt = f"""
Analyze the user's query and list the names of all people or specific topics mentioned.
These are the subjects of the query.
Respond with a comma-separated list of names/topics. If the user is asking about themself, respond with "self".

Query: "{query}"

Subjects:"""
        try:
            payload = {"messages": [{"role": "user", "content": entity_prompt}], "temperature": 0.0, "n_predict": 48}
            resp = requests.post(serverconfig.LLAMA_CPP_CHAT_URL, json=payload, timeout=60)
            resp.raise_for_status()
            entities_raw = resp.json()['choices'][0]['message']['content'].strip()
            return [_sanitize_for_filename(e.strip()) for e in entities_raw.split(',') if e.strip()]
        except Exception as e:
            print(f"ENTITY_EXTRACTION_ERROR: {e}")
            return []

    ### NEW: The 'intelligent_recall' function that solves the "Two Sarahs" problem ###
    def intelligent_recall(self, user_id, query, top_k=3, threshold=0.5):
        if not self.vectors: return []
        try:
            entities_in_query = self._extract_entities_from_query(query)
            if not entities_in_query:
                print(f"[RECALL] No entities extracted from query: '{query}'")
                return []
            
            print(f"[RECALL] User '{user_id}' querying about: {entities_in_query}")
            
            with self.lock:
                log_df = self.master_log.copy()

            # --- THE CORE INTELLIGENCE ---
            # This logic block is the new "brain" for recall.
            # It filters the entire memory log based on who is asking and what they are asking about.
            if 'self' in entities_in_query:
                # Find memories where the user is either the speaker OR the subject.
                relevant_memories_df = log_df[(log_df['speaker_id'] == user_id) | (log_df['entity_id'] == user_id)]
            else:
                # Find memories SPOKEN BY THE CURRENT USER about the specific entities queried.
                # This is what differentiates Scott's "Sarah" from Fred's "Sarah".
                relevant_memories_df = log_df[(log_df['speaker_id'] == user_id) & (log_df['entity_id'].isin(entities_in_query))]

            if relevant_memories_df.empty:
                print(f"[RECALL] No relevant memories found for user '{user_id}' on topics {entities_in_query}.")
                return []

            # Perform vector search ONLY on this highly relevant subset of memories
            relevant_uuids = relevant_memories_df['uuid'].tolist()
            filtered_vecs = {uuid: self.vectors[uuid] for uuid in relevant_uuids if uuid in self.vectors}

            if not filtered_vecs: return []

            query_vec = self._get_embedding(query)
            
            # Perform similarity search
            uuids_list = list(filtered_vecs.keys())
            vecs_array = np.array(list(filtered_vecs.values()))
            sim = cosine_similarity(query_vec.reshape(1, -1), vecs_array)[0]
            
            top_indices = np.argsort(sim)[-top_k:][::-1]
            results = [log_df.loc[log_df['uuid'] == uuids_list[i], 'text'].iloc[0] for i in top_indices if sim[i] >= threshold]
            
            return results
        except Exception as e:
            import traceback; traceback.print_exc()
            return [f"LTM_RECALL_ERROR: {e}"]

    # --- User signature logic (enroll, identify) remains the same ---
    def enroll_user(self, user_id, conversation_history):
        if len(conversation_history) < 3: return
        try:
            with self.lock:
                user_messages = [msg['content'] for msg in conversation_history if msg['role'] == 'user']
                if not user_messages: return
                message_vectors = [self._get_embedding(msg) for msg in user_messages]
                self.signatures[user_id] = np.mean(message_vectors, axis=0)
                save_file(self.signatures, serverconfig.SIGNATURES_FILE_PATH)
            print(f"ENROLL: Signature for '{user_id}' saved successfully.")
        except Exception as e: print(f"ENROLL_ERROR: {e}")

    def identify_user(self, current_message_text, confidence_threshold=0.75):
        if not self.signatures: return None
        try:
            with self.lock:
                guest_vector = self._get_embedding(current_message_text).reshape(1, -1)
                if not self.signatures: return None # Check again after lock
                known_users, signature_vectors = list(self.signatures.keys()), np.array(list(self.signatures.values()))
            if signature_vectors.size == 0: return None
            similarities = cosine_similarity(guest_vector, signature_vectors)[0]
            best_match_index = np.argmax(similarities)
            best_score = similarities[best_match_index]
            if best_score >= confidence_threshold: return known_users[best_match_index]
            return None
        except Exception as e: print(f"ID_ERROR: {e}"); return None