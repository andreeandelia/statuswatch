FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATUSWATCH_DB=/data/statuswatch.db

WORKDIR /app

# Dependențele întâi, ca Docker să refolosească stratul când se schimbă doar codul
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Utilizator fără drepturi de root + folder pentru baza de date
RUN useradd --create-home appuser && mkdir /data && chown appuser /data

COPY app ./app
COPY services.json .

USER appuser
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]