import os
from pathlib import Path
import numpy as np
from typing import List
from sentence_transformers import util
from transformers import pipeline

BASE_DIR = Path("/data/vector_store")

# LLM для генерации summary (можно заменить на свою)
summarizer = pipeline("text-generation", model="gemma3:4b")


def load_latest_embeddings_with_texts(team_folder: Path, top_k: int = 3):
    files = sorted(team_folder.glob("emb_*.npz"), key=os.path.getctime, reverse=True)
    embeddings = []
    chunks = []
    for f in files[:top_k]:
        data = np.load(f, allow_pickle=True)
        embeddings.append(data["embedding"])
        chunks.extend(data["chunks"].tolist())
    return np.vstack(embeddings), chunks


def analyze_team_reports(team_name: str) -> str:
    team_folder = BASE_DIR / team_name
    if not team_folder.exists():
        return f"❌ Команда '{team_name}' не найдена"

    try:
        embeddings, chunks = load_latest_embeddings_with_texts(team_folder)
    except Exception as e:
        return f"⚠️ Ошибка загрузки эмбеддингов: {e}"

    if len(chunks) == 0 or embeddings.shape[0] == 0:
        return "⚠️ Нет данных для анализа."

    # Вычисляем центроид и похожие тексты
    centroid = np.mean(embeddings, axis=0)
    similarities = util.cos_sim(embeddings, centroid)
    top_indices = similarities.squeeze().argsort()[-10:][::-1]
    top_chunks = [chunks[i] for i in top_indices]

    summary_input = "\n".join(top_chunks)
    result = summarizer(summary_input, max_length=200, do_sample=False)[0]["generated_text"]

    return f"🧠 Анализ отчётов команды '{team_name}':\n{result}"


# ===== Пример использования =====
if __name__ == "__main__":
    team_name = "Депозиты (стадия ДО открытия) и FX (основная стадия)."
    from report_storage_manager import sanitize_folder_name
    readable_name = sanitize_folder_name(team_name)
    print(analyze_team_reports(readable_name))
