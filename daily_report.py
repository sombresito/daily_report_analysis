#!/usr/bin/env python3
"""
daily_report.py: Fetch report JSON via Swagger API (via UUID or full URLs),
analyze with RAG + local model, and send analysis back via Swagger API.

Usage:
  # Using a stored UUID (requires GET_URL_BASE and POST_URL_BASE env vars):
  python daily_report.py --uuid REPORT_UUID --user USER --password PASS [--chunk-size CHUNK_SIZE] [--top-k TOP_K]

  # Or specify full URLs directly:
  python daily_report.py --get-url GET_URL --post-url POST_URL --user USER --password PASS [--chunk-size CHUNK_SIZE] [--top-k TOP_K]

Requires:
  pip install requests sentence-transformers faiss-cpu
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime
from collections import Counter

# Try to import RAG dependencies
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
except ImportError:
    SentenceTransformer = None
    faiss = None

# Enable UTF-8 output on Windows
if os.name == 'nt':
    os.system('chcp 65001 > nul')
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

def load_report_from_api(get_url, auth):
    resp = requests.get(get_url, auth=auth, headers={'Accept': 'application/json'})
    resp.raise_for_status()
    return resp.json()

def send_analysis_to_api(post_url, auth, payload_list):
    resp = requests.post(post_url, auth=auth, json=payload_list,
                         headers={'Content-Type': 'application/json'})
    resp.raise_for_status()
    return resp

def flatten_report(report: dict) -> list[dict]:
    """
    Преобразует вложенную структуру отчёта в плоский список.
    Каждый элемент — это словарь:
        {
         "path": "root > child > ...",
         "status": "<status>",
         "uid": "<uid>"
        }
    """
    items: list[dict] = []

    def recurse(node: dict, path: list[str]):
        name = node.get("name")
        # накапливаемый путь: только если у узла есть имя
        new_path = path + [name] if name else path
        # если узел содержит поле status — это "листьевой" узел теста
        if "status" in node:
            items.append({
                "path": " > ".join(new_path),
                "status": node["status"],
                "uid": node.get("uid", "")
            })
        # рекурсивно обрабатываем всех детей, если есть
        for child in node.get("children", []):
            recurse(child, new_path)

    # стартуем рекурсию с пустого пути
    recurse(report, [])
    return items


def chunk_items(items: list[dict], chunk_size: int) -> list[str]:
    """
    Разбивает список элементов (из flatten_report) на куски текста длиной <= chunk_size символов.
    Каждый элемент items — словарь с ключами path, status, uid.
    Возвращает список строк, готовых для передачи в модель.
    """
    chunks: list[str] = []
    current = ""

    for it in items:
        # Формируем текст для одного теста
        txt = f"{it['path']} [{it['status']}]"
        if it.get("uid"):
            txt += f" (uid={it['uid']})"

        # Если добавление переполнит текущий chunk — сохраняем его и начинаем новый
        if len(current) + len(txt) + 1 > chunk_size:
            if current:
                chunks.append(current)
            current = txt
        else:
            # добавляем в текущий, разделяя переводом строки
            current = f"{current}\n{txt}" if current else txt

    # последний непустой кусок
    if current:
        chunks.append(current)

    return chunks


def build_index(chunks):
    if SentenceTransformer is None or faiss is None:
        return None, None
    try:
        model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
        embs = model.encode(chunks, convert_to_numpy=True)
        index = faiss.IndexFlatL2(embs.shape[1])
        index.add(embs)
        return index, model
    except:
        return None, None

def retrieve_chunks(query, chunks, index, model, top_k):
    if index is None or model is None:
        return chunks[:top_k]
    q_emb = model.encode([query], convert_to_numpy=True)
    _, I = index.search(q_emb, top_k)
    return [chunks[i] for i in I[0] if i < len(chunks)]

def ask_model_stream(prompt: str,
                     context: str,
                     model_name: str = "gemma3:1b",
                     host: str = "localhost",
                     port: int = 11434,
                     max_tokens: int = 2048) -> str:
    """
    Запрос к модели через ollama API в режиме streaming.
    Если стриминг не даёт данных, переходит на non-stream.
    """
    print(f"[DEBUG] Длина контекста (символов): {len(context)}")
    # (debug сохраняем контекст в last_context.txt ...)

    url = f"http://{host}:{port}/v1/completions"
    payload = {
        "model": model_name,
        "prompt": f"{context}\n\nЗапрос: {prompt}\n\nОтвет:",
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "stream": True
    }

    try:
        resp = requests.post(url, json=payload, stream=True)
        resp.raise_for_status()
    except Exception:
        # при сбое стрима сразу на non-stream:
        return ask_model_nonstream(prompt, context, model_name, host, port, max_tokens)

    full_response = ""
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.strip().startswith("data:"):
            continue
        data_str = line.strip()[len("data:"):].strip()
        try:
            chunk = json.loads(data_str)
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content", "")
            full_response += content
            print(content, end="", flush=True)
        except json.JSONDecodeError:
            continue

    print()  # перевод строки после стрима

    # **здесь** добавляем return при пустом ответе:
    if not full_response.strip():
        print("[DEBUG] Streaming вернул пустой ответ, пробую non-stream.")
        return ask_model_nonstream(prompt, context, model_name, host, port, max_tokens)

    return full_response


def ask_model_nonstream(prompt: str, context: str,
                         model_name: str, host: str, port: int,
                         max_tokens: int) -> str:
    """
    Запрос к модели без стриминга, возвращает полный ответ.
    """
    url = f"http://{host}:{port}/v1/completions"
    payload = {
        "model": model_name,
        # Здесь важно: сначала контекст, потом ровно "Запрос: <prompt>"
        "prompt": f"{context}\n\nЗапрос: {prompt}\n\nОтвет:",
        "max_tokens": max_tokens,
        "temperature": 0.2
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0].get("text", "").strip()

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--uuid', help='Report UUID; requires GET_URL_BASE and POST_URL_BASE env vars')
    group.add_argument('--get-url', help='Full GET URL for report JSON')
    parser.add_argument('--post-url', help='Full POST URL for analysis')
    parser.add_argument('--user', required=True)
    parser.add_argument('--password', required=True)
    parser.add_argument('--chunk-size', type=int, default=128)
    parser.add_argument('--top-k', type=int, default=20)
    parser.add_argument('--model', default='gemma3:1b')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=11434)
    parser.add_argument('--max-tokens', type=int, default=2048)
    args = parser.parse_args()

    auth = (args.user, args.password)

    if args.uuid:
        base_get = os.getenv('GET_URL_BASE')
        base_post = os.getenv('POST_URL_BASE')
        if not base_get or not base_post:
            print('Error: GET_URL_BASE and POST_URL_BASE must be set when using --uuid', file=sys.stderr)
            sys.exit(1)
        uuid = args.uuid
        get_url = f"{base_get}/{uuid}/suites/json"
        post_url = f"{base_post}/{uuid}"
    else:
        get_url = args.get_url
        post_url = args.post_url
        if not post_url:
            print('Error: --post-url is required when using --get-url', file=sys.stderr)
            sys.exit(1)

    report = load_report_from_api(get_url, auth)
    items = flatten_report(report)

    cnt = Counter(it['status'] for it in items)
    failed = cnt.get('failed', 0)
    broken = cnt.get('broken', 0)
    flaky  = cnt.get('flaky', 0)
    passed = len(items) - (failed + broken + flaky)
    intro = f"failed: {failed}, broken: {broken}, flaky: {flaky}, passed: {passed}"

    chunks = chunk_items(items, args.chunk_size)
    index, embed_model = build_index(chunks)

    date_str = datetime.now().strftime('%Y-%m-%d')
    prompt_main = f"Общий анализ результатов тестирования за {date_str} и рекомендации."
    query = intro + ' | ' + prompt_main
    top_chunks = retrieve_chunks(query, chunks, index, embed_model, args.top_k)
    context = '\n'.join(top_chunks)

    analysis = ask_model_stream(
        prompt_main, context,
        args.model, args.host, args.port, args.max_tokens
    )

    payload_list = [{
        'rule': date_str,
        'message': intro + '\n\n' + analysis
    }]
    resp = send_analysis_to_api(post_url, auth, payload_list)
    print(f"Posted analysis, HTTP {resp.status_code}")

if __name__ == '__main__':
    main()
