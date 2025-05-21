import json
from report_storage_manager import extract_team_name, sanitize_folder_name
from vectorizer import vectorize_report


def process_report(uuid: str, report_json: dict):
    # Извлекаем название команды
    team_name = extract_team_name(report_json)
    team_folder_name = sanitize_folder_name(team_name)

    # Векторизуем и сохраняем векторное представление
    vectorize_report(report_json, team_folder_name)

    print(f"🎯 Завершена обработка отчёта для команды: {team_name}")


# ===== Пример использования =====
if __name__ == "__main__":
    # Пример загрузки отчёта из файла (в проде отчёт приходит по UUID)
    with open("example_report.json", encoding="utf-8") as f:
        report = json.load(f)

    process_report("dummy-uuid", report)
