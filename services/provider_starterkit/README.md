# Digital Product Memory Provider Starterkit

This folder is a minimal template for building a new Digital Product Memory data provider.

The provider exposes:

- `GET /products/{product_id}` for product passport data
- `GET /products` for a lightweight product list
- `GET /.well-known/circthread-service` for registry auto-discovery
- `GET /metadata` with the same metadata for easier manual testing
- `GET /health` for Docker health checks

## Run Locally

```bash
cd services/provider_starterkit
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8020
```

Register it from the frontend Registry page with:

```text
http://host.docker.internal:8020
```

If the whole stack runs in Docker Compose, add the service to `docker-compose.yml` and register it with:

```text
http://provider-starterkit:8020
```

## Docker Compose Snippet

```yaml
provider-starterkit:
  build:
    context: .
    dockerfile: services/provider_starterkit/Dockerfile
  container_name: circthread-provider-starterkit
  ports:
    - "8020:8020"
  networks:
    - circthread-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8020/health"]
    interval: 10s
    timeout: 5s
    retries: 5
```

## Adapt It

Replace `app/product_data.py` with your real data source. You can return partial passports. For example, one provider might only return repair history, while another returns materials or compliance data.

Keep this endpoint stable:

```text
GET /products/{product_id}
```

Return JSON keys that match the shared passport fields in `shared/models.py` where possible. The Resolver merges all provider responses for the same product ID.
