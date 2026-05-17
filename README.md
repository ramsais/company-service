# Company Service

A high-performance FastAPI microservice designed for AWS ECS (Fargate). It manages company records using a thread-safe local JSON storage pattern and enriches data from an external Deal API.

## Features

- **FastAPI Core**: Modern Python 3.10+ syntax and asynchronous request handling.
- **Local JSON Storage**: Thread-safe persistence using `fcntl` file locking and atomic writes (temp file + rename).
- **Deal API Integration**: Asynchronous enrichment of company data with resilient fallbacks.
- **Pydantic v2**: Strict data validation for all DTOs and internal models.
- **Global Exception Handling**: Structured error responses using custom application exceptions.
- **Dockerized**: Optimized production-ready Dockerfile for AWS ECS.

## Project Structure

```text
company-service/
├── app/
│   ├── exceptions.py      # Custom exceptions and handlers
│   ├── routers/           # API endpoints (FastAPI routers)
│   ├── schemas/           # Pydantic models (DTOs)
│   ├── services/          # Business logic & external clients
│   │   ├── company_service.py
│   │   ├── config.py      # Pydantic-settings configuration
│   │   ├── deal_service.py # Deal API client
│   │   └── storage_service.py # JSON storage logic
│   └── storage/           # Local JSON persistence directory
├── main.py                # Application entry point
├── Dockerfile             # Container definition
└── requirements.txt       # Dependencies
```

## Getting Started

### Prerequisites

- Python 3.10+
- Docker (optional)

### Local Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python main.py
   ```
   The service will be available at `http://localhost:8000`.

3. Access API Documentation:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

### Configuration

Configuration is managed via environment variables using `pydantic-settings`.

| Variable | Default | Description |
|----------|---------|-------------|
| `DEAL_SERVICE_URL` | `http://deal-service.local` | Base URL for the Deal API |
| `STORAGE_FILE_PATH` | `app/storage/companies.json` | Path to the local JSON storage file |

## Error Handling

The service uses a centralized exception handler to return structured JSON responses:

```json
{
  "error": "ResourceNotFoundException",
  "message": "Company with id 123 not found",
  "details": {}
}
```

## Recommendations for Improvement

1. **Structured Logging**: Implement a library like `structlog` for machine-readable logs in AWS CloudWatch.
2. **Distributed Tracing**: Integrate AWS X-Ray or OpenTelemetry to trace requests across microservices.
3. **Caching**: Use an in-memory cache (like `cachetools`) for Deal API responses to reduce latency and downstream load.
4. **Validation**: Add more granular validation for fields like `website` (URL format) and `location`.
5. **Unit & Integration Tests**: Implement a full test suite using `pytest` and `httpx.AsyncClient` for integration testing.

## Generating the Deal Service

To create a matching Deal Service, follow a similar architecture:

1. **Stack**: FastAPI + Pydantic v2.
2. **Endpoints**:
   - `GET /deals?company_id={id}`: Returns a list of deals for a specific company.
3. **Resiliency**: Ensure it can handle high concurrency if many services depend on it.
4. **Mocking**: For development, you can use a simple FastAPI app that returns static JSON deals.

Example Deal Schema:
```python
class Deal(BaseModel):
    id: str
    title: str
    amount: float
    status: str # e.g., "Open", "Closed", "Won", "Lost"
```
