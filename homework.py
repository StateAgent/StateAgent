import glob
import os
import time
import threading
import numpy as np
import pandas as pd
import faiss
from safetensors.numpy import load_file

MEM_DIR = r"A:\\Station\\Memory"
CHECK_INTERVAL = 600  # 10 minutes

lock = threading.Lock()

def process_parquets():
    with lock:
        files = glob.glob(os.path.join(MEM_DIR, "mem_*.parquet"))
        for path in files:
            try:
                df = pd.read_parquet(path)
                if "embedding" not in df.columns:
                    continue
                vectors = np.stack(df["embedding"].to_list()).astype(np.float32)
                dim = vectors.shape[1]
                index = faiss.IndexFlatL2(dim)
                index.add(vectors)
                faiss.write_index(index, path.replace(".parquet", ".faiss"))
            except Exception as e:
                print(f"Homework error processing {path}: {e}")

def homework_loop():
    while True:
        process_parquets()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    homework_loop()
