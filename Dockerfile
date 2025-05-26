FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    && update-ca-certificates

WORKDIR /app

COPY . /app
COPY models/all-MiniLM-L6-v2 /app/models/all-MiniLM-L6-v2

RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8000"]