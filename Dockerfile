# Dockerfile
FROM python:3.10-slim

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    git \
    ca-certificates \
    && update-ca-certificates

# Копируем файлы проекта
WORKDIR /app
COPY . /app

# Устанавливаем зависимости с обходом SSL-проверки
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

# Открываем порт для FastAPI
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8000"]