#!/bin/bash

# Запуск сервиса RAG для анализа отчётов

echo "[✔] Стартуем FastAPI-сервис..."
exec uvicorn main_api:app --host 0.0.0.0 --port 8000
