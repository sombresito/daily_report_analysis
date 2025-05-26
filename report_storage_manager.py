import os
import json
from pathlib import Path

BASE_DIR = Path("/data/vector_store")
MAX_REPORTS = 3

def sanitize_folder_name(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in " _-().").strip()

def extract_team_name(report_json: dict) -> str:
    try:
        return report_json["children"][0]["name"]
    except (KeyError, IndexError):
        raise ValueError("Не удалось извлечь название команды из отчёта")