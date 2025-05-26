import os
import sys
import json
import requests
from datetime import datetime
from report_storage_manager import extract_team_name, sanitize_folder_name
from vectorizer import vectorize_report
from analyzer import analyze_team_reports

# Настройки из окружения
GET_URL_BASE = os.getenv('GET_URL_BASE')
POST_URL_BASE = os.getenv('POST_URL_BASE')
ALLURE_USER = os.getenv('ALLURE_USER')
ALLURE_PASS = os.getenv('ALLURE_PASS')

MODEL_HOST = os.getenv('MODEL_HOST', 'localhost')
MODEL_PORT = os.getenv('MODEL_PORT', '11434')

def load_report_by_uuid(uuid):
    get_url = f"{GET_URL_BASE}/{uuid}/suites/json"
    print(f"📥 Загружаем отчёт: {get_url}")
    response = requests.get(get_url, auth=(ALLURE_USER, ALLURE_PASS), headers={"Accept": "application/json"})
    response.raise_for_status()
    return response.json()

def post_analysis(uuid, message):
    post_url = f"{POST_URL_BASE}/{uuid}"
    payload = [{
        'rule': datetime.now().strftime('%Y-%m-%d'),
        'message': message
    }]
    response = requests.post(post_url, auth=(ALLURE_USER, ALLURE_PASS),
                             json=payload, headers={'Content-Type': 'application/json'})
    response.raise_for_status()
    print(f"📤 Отправлен анализ (HTTP {response.status_code})")

def main():
    if len(sys.argv) < 2:
        print("Usage: python daily_rag_report.py <uuid>")
        sys.exit(1)

    uuid = sys.argv[1]
    report_json = load_report_by_uuid(uuid)

    team_name = extract_team_name(report_json)
    folder_name = sanitize_folder_name(team_name)

    print(f"📂 Команда: {team_name} → папка {folder_name}")

    # Сохраняем новый эмбеддинг
    vectorize_report(report_json, folder_name)

    # Анализируем последние 1–3 отчёта этой команды
    summary = analyze_team_reports(folder_name)

    print("📄 Summary готов:")
    print(summary)

    # Отправляем обратно в Allure
    post_analysis(uuid, summary)

if __name__ == "__main__":
    main()
