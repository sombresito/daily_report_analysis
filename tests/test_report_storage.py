import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import shutil
import time
from report_storage_manager import save_report, BASE_DIR, sanitize_folder_name

def setup_module(module):
    # Очистка тестового окружения
    test_team = sanitize_folder_name("Тестовая команда")
    test_dir = BASE_DIR / test_team
    if test_dir.exists():
        shutil.rmtree(test_dir)

def test_save_and_cleanup_reports():
    test_report = {
        "uid": "test-uid",
        "name": "suites",
        "children": [
            {
                "name": "Тестовая команда",
                "children": [
                    {
                        "name": "Subtest"
                    }
                ]
            }
        ]
    }

    for _ in range(5):
        save_report("test-uuid", test_report)
        time.sleep(1)  # гарантируем разные имена файлов

    test_team_dir = BASE_DIR / sanitize_folder_name("Тестовая команда")
    assert test_team_dir.exists(), "Папка команды должна существовать"

    report_files = list(test_team_dir.glob("report_*.json"))
    assert len(report_files) == 3, f"Ожидалось 3 файла, найдено {len(report_files)}"

    # Проверим что все файлы корректные JSON
    for report_path in report_files:
        with open(report_path, encoding="utf-8") as f:
            data = json.load(f)
            assert "uid" in data
            assert "children" in data
