FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
# Configure pip to trust PyPI hosts and bypass SSL verification
RUN pip config set global.trusted-host pypi.org \
    && pip config set global.trusted-host files.pythonhosted.org \
    && pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

COPY daily_report.py uuid_service.py entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

VOLUME /data
EXPOSE 5000

ENTRYPOINT ["/app/entrypoint.sh"]
