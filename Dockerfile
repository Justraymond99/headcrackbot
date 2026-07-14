FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-headcrack.txt ./
RUN pip install --no-cache-dir -r requirements-headcrack.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV HEADCRACK_DATABASE_URL=sqlite:///data/headcrack_ai.sqlite3
ENV HEADCRACK_WAREHOUSE_URL=sqlite:///data/headcrack_warehouse.sqlite3

EXPOSE 8000 8501

CMD ["python", "-m", "headcrack_ai.api.app"]
