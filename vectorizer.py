import os
import json
from pathlib import Path
from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np
import time

BASE_DIR = Path("/data/vector_store")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MAX_EMBEDDINGS = 3

model = SentenceTransformer(MODEL_NAME)


def extract_text_chunks(report_json: dict) -> List[str]:
    chunks = []

    def recurse(node):
        if "name" in node:
            chunks.append(node["name"])
        if "status" in node:
            chunks.append(f"Status: {node['status']}")
        if "message" in node:
            chunks.append(f"Message: {node['message']}")
        if "children" in node:
            for child in node["children"]:
                recurse(child)

    recurse(report_json)
    return chunks


def save_embedding(team_name: str, embedding: np.ndarray, chunks: List[str]):
    team_folder = BASE_DIR / team_name
    team_folder.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = team_folder / f"emb_{timestamp}.npz"
    np.savez_compressed(path, embedding=embedding, chunks=np.array(chunks))
    print(f"💾 Сохранён векторный файл: {path.name}")

    cleanup_old_embeddings(team_folder)


def cleanup_old_embeddings(folder: Path):
    files = sorted(folder.glob("emb_*.npz"), key=os.path.getctime, reverse=True)
    for old_file in files[MAX_EMBEDDINGS:]:
        try:
            old_file.unlink()
            print(f"🗑️ Удалён старый эмбеддинг: {old_file.name}")
        except Exception as e:
            print(f"⚠️ Не удалось удалить {old_file.name}: {e}")


def vectorize_report(report_json: dict, team_folder_name: str):
    chunks = extract_text_chunks(report_json)
    if not chunks:
        print("⚠️ Нет текста для векторизации.")
        return

    embedding = model.encode(chunks, show_progress_bar=False)
    save_embedding(team_folder_name, np.array(embedding).astype("float32"), chunks)
