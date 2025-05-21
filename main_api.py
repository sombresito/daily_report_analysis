from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from report_storage_manager import extract_team_name, sanitize_folder_name
from vectorizer import vectorize_report
from analyzer import analyze_team_reports

app = FastAPI()


class ReportInput(BaseModel):
    uuid: str  # Пока не используется, но можно логировать
    report: dict


@app.post("/analyze")
def analyze_report(payload: ReportInput):
    try:
        # Извлекаем имя команды и папку
        team_name = extract_team_name(payload.report)
        folder_name = sanitize_folder_name(team_name)

        # Векторизация и сохранение эмбеддингов
        vectorize_report(payload.report, folder_name)

        # Анализ по последним 1-3 отчетам
        summary = analyze_team_reports(folder_name)
        return {"team": team_name, "summary": summary}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    return {"status": "RAG-сервис готов к приёму отчётов на анализ."}
