# Zango Adaptive Assessment Engine Microservice

The **Adaptive Assessment Engine** is a specialized, independent microservice developed with **Python 3.12+** and **FastAPI**. It is an integral component of the Zango educational platform, designed to measure student cognitive and technical capabilities using Computerized Adaptive Testing (CAT).

---

## 1. Core Capabilities & Architecture

- **Independent Microservice:** Operates autonomously with its own database persistence and lifecycle.
- **Ecosystem Integration:** Connects with the Zango Java/Spring ecosystem via:
  - **Netflix Eureka Service Discovery:** Automatically registers as `ASSESSMENT-SERVICE`, maintains lease renewal via 30s heartbeats, and deregisters gracefully.
  - **Spring Cloud Gateway:** External requests route through Gateway (`8080`), passing RS256 JWT tokens and `X-Correlation-ID`.
  - **Shared Security:** Validates JWT access tokens signed by `auth-service` using the shared RSA public key (`public.pem`).
  - **Standard Problem Details:** Adheres strictly to **RFC 7807 (`application/problem+json`)** matching the Zango platform error taxonomy.
- **Cognitive Dimensions:**
  - `logical_reasoning`
  - `algorithmic_thinking`
  - `problem_solving`
  - `spatial_reasoning`
  - `computational_thinking`
- **Internal Layered Architecture:**
  - `app/api/`: Web layer, versioned routes (`/api/v1`), schema validation, health probes.
  - `app/domain/`: Pure domain types, enums, business invariants.
  - `app/application/`: Orchestration services and transactional use cases.
  - `app/engine/`: Pure, stateless CAT algorithms (protocols for Selector, Estimator, Stopping, Evaluator).
  - `app/infrastructure/`: Persistence (SQLAlchemy 2.0 Async, Alembic), Security (JWT), Eureka Client, Structured Logging.

---

## 2. Quickstart: Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 16 (or SQLite for local unit testing)

### Installation
```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env

# 4. Run database migrations
alembic upgrade head

# 5. Start the service
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)
- Readiness check: [http://localhost:8000/ready](http://localhost:8000/ready)

---

## 3. Running with Docker Compose

To run the assessment service alongside its database on the shared `zango` network:

```bash
docker compose up -d --build
```

---

## 4. Running Tests

```bash
pytest -v
```
