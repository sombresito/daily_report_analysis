import os
import json
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/data/vector_store")  # путь можно сделать через ENV
MAX_REPORTS = 3


def sanitize_folder_name(name: str) -> str:
    # Удалим символы, которые могут ломать файловую систему
    return "".join(c for c in name if c.isalnum() or c in " _-()[]{}.").strip()


def extract_team_name(report_json: dict) -> str:
    try:
        return report_json["children"][0]["name"]
    except (KeyError, IndexError):
        raise ValueError("Не удалось извлечь название команды из отчёта")


def save_report(uuid: str, report_content: dict):
    team_name = extract_team_name(report_content)
    team_folder = BASE_DIR / sanitize_folder_name(team_name)
    team_folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"report_{timestamp}.json"
    report_path = team_folder / report_filename

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_content, f, ensure_ascii=False, indent=2)

    print(f"✅ Сохранён отчёт: {report_path}")

    clean_old_reports(team_folder)


def clean_old_reports(team_folder: Path):
    reports = sorted(team_folder.glob("report_*.json"), key=os.path.getctime, reverse=True)
    if len(reports) > MAX_REPORTS:
        for old_report in reports[MAX_REPORTS:]:
            try:
                old_report.unlink()
                print(f"🗑️ Удалён старый отчёт: {old_report.name}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить {old_report.name}: {e}")


# ===== Пример использования =====
if __name__ == "__main__":
    # Пример загрузки отчёта из файла (в боевом режиме приходит из запроса по UUID)
    example_path = "example_report.json"
    with open(example_path, encoding="utf-8") as f:
        report_json = json.load(f)

    save_report("dummy-uuid", report_json)
