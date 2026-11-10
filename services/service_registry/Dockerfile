FROM python:3.12-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy shared package
COPY shared/ /app/shared/

# Copy service
COPY services/service_registry/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/service_registry/app/ /app/app/
COPY services/service_registry/data/ /app/data/
COPY services/service_registry/data/registry.json /app/seed/registry.json

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
