FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY shared/ /app/shared/
COPY services/repair_service_provider/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/repair_service_provider/app/ /app/app/

EXPOSE 8025

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8025"]
