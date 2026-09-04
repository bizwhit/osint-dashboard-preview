FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir maigret sherlock-project holehe phoneinfoga theHarvester
RUN mkdir -p /app/data /app/reports && curl -fsSL -o /app/data/wmn-data.json https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json || echo '{"sites": []}' > /app/data/wmn-data.json
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
