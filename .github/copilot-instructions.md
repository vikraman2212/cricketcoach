# GitHub Copilot Instructions — AI Cricket Coach

## Repository Overview

This monorepo is an AI-powered cricket coaching system that calculates bowling speed and biomechanics from phone video. It comprises three sub-projects and shared ML training code:

```
cricketcoach/
├── middleware/              # Spring Boot 4 (Java 25) — orchestration layer
├── speedtracking-api/      # FastAPI (Python 3.11) — CV/physics inference
├── balltracker_trainer/    # ML training (Python) — YOLOv11 ball + pose
│   ├── ball-detector/      # Cricket ball detection with SAHI
│   ├── bowler-pose/        # Bowling biomechanics keypoints
│   └── tools/              # Video download & frame extraction utilities
├── .github/workflows/      # CI: ci.yml (test on push/PR), require-tests.yml
├── docker-compose.yml      # Dev stack: MinIO + speedtracking-api + middleware
└── req_docs/               # PRD, ERD, Delivery Plan, Architecture Decisions
```

## Architecture

The async data pipeline:
1. Flutter uploads video directly to MinIO via presigned PUT URL (from middleware)
2. MinIO fires `s3:ObjectCreated:Put` webhook → FastAPI (`POST /webhooks/minio`)
3. FastAPI downloads video, runs YOLO+SAHI → ByteTrack → physics, publishes SSE events
4. Flutter listens to `GET /api/v1/deliveries/{id}/stream` on middleware (SSE relay)

---

## Sub-Project 1: `middleware/` — Spring Boot 4

**Language:** Java 25 | **Framework:** Spring Boot 4.0.3 | **Build:** Maven (`./mvnw`)

### Code Conventions
- Use Java records for immutable model types (see `DeliveryAnalysisResponse`)
- Annotate controllers with `@RestController` and `@RequestMapping`
- Use `WebClient` (not `RestTemplate`) for all HTTP calls to FastAPI
- Handle errors via `GlobalExceptionHandler` (`@RestControllerAdvice`)
- Use `@Value("${property:default}")` for all configurable values; never hardcode URLs or credentials
- Use `ConcurrentHashMap` for in-memory state; comment TTL expectations inline
- Virtual threads are enabled via `spring.threads.virtual.enabled=true`

### Key Packages
- `controller/` — HTTP endpoints
- `service/` — Business logic + external HTTP clients
- `model/` — Request/response records (use `@JsonProperty` for snake_case fields)
- `exception/` — Custom exceptions (extend `RuntimeException`)
- `advice/` — `GlobalExceptionHandler` for consistent error responses

### Testing
- Test classes live in `middleware/src/test/java/io/aicoach/middleware/`
- Use `@SpringBootTest` with H2 datasource (configured automatically)
- Use `@WebMvcTest` for controller slice tests
- Use `MockitoExtension` and `@MockitoBean` for service mocks
- Run: `cd middleware && ./mvnw --batch-mode test`

### Adding a New Endpoint
1. Create a controller in `controller/`
2. Create a service in `service/`
3. Add request/response records in `model/`
4. Add exception handler in `GlobalExceptionHandler` if new exception type needed
5. **Always** add a matching test class in `src/test/java/`

---

## Sub-Project 2: `speedtracking-api/` — FastAPI

**Language:** Python 3.11 | **Framework:** FastAPI ≥0.115 | **Package manager:** pip

### Code Conventions
- Use Pydantic v2 `BaseModel` for all request/response schemas (see `schemas.py`)
- Use `model_config = ConfigDict(extra="ignore")` on input models
- Use `@lru_cache` for singleton settings/config (see `config.py`)
- All endpoint handler functions must be `async def`
- Use `BackgroundTasks` for fire-and-forget async processing (never `asyncio.create_task` directly in a route)
- Use `sse_starlette.sse.EventSourceResponse` for SSE streaming endpoints
- Store delivery pipeline state in an in-memory dict with `asyncio.Lock` for thread safety
- Config is loaded from environment variables via `ServiceSettings` (Pydantic `BaseModel`)

### Project Structure
```
speedtracking-api/
├── app/
│   ├── main.py        # FastAPI app, routes
│   ├── config.py      # Settings (lru_cache), load_default_inference_config()
│   ├── schemas.py     # Pydantic request/response models
│   ├── services.py    # BootstrapAnalysisService (replace with real inference)
│   └── pipeline.py    # Async delivery pipeline + in-memory state store
├── tests/
│   └── test_*.py      # pytest test files
├── models/            # ML model weights (gitignored, mounted at /models in Docker)
└── requirements.txt
```

### Data Pipeline (`pipeline.py`)
The pipeline processes a delivery asynchronously:
1. Emit `uploaded` event
2. Download video bytes from MinIO via `boto3` S3 client
3. Emit `detecting` event → run ball detection (YOLO+SAHI when model is available)
4. Emit `tracking` event → ByteTrack + Kalman filter
5. Emit `calculating` event → physics engine
6. Emit `complete` event with `AnalyzeDeliveryResponse` payload
7. Delete video from MinIO (cleanup)

The `DeliveryStore` in `pipeline.py` holds `delivery_id → DeliveryState`. Consumers (SSE endpoint) poll the store.

### MinIO / S3 Client
Use `boto3` with a custom endpoint URL read from environment variables:
```python
MINIO_ENDPOINT_URL = os.environ.get("MINIO_ENDPOINT_URL", "http://minio:9000")
MINIO_ACCESS_KEY   = os.environ.get("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY   = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")
```

### Testing
- Test files live in `speedtracking-api/tests/test_*.py`
- Use `pytest` + `pytest-asyncio` + `httpx.AsyncClient`
- Use `AsyncClient(transport=ASGITransport(app=app))` for in-process testing
- Run: `cd speedtracking-api && pytest tests/ -v`

### Adding a New Endpoint
1. Add schema to `schemas.py`
2. Implement logic in `pipeline.py` or a new service module
3. Register route in `main.py`
4. **Always** add a test in `tests/test_*.py`

---

## Sub-Project 3: `balltracker_trainer/` — ML Training

**Language:** Python 3.11+ | **Framework:** Ultralytics YOLOv11

### `ball-detector/` — Cricket Ball Detection
- Model: YOLOv11n fine-tuned for small object detection
- Uses SAHI (Slicing Aided Hyper Inference) to handle 1080p → 320×320 slices
- ByteTrack + Kalman filter for inter-frame tracking
- Target: mAP@50 ≥ 0.7
- Training config: `ball-detector/configs/training_config.yaml`
- Inference config: `ball-detector/configs/inference_config.yaml` (loaded by speedtracking-api at startup)

### `bowler-pose/` — Bowling Biomechanics
- Model: YOLOv11s-Pose with 17 COCO keypoints
- Focus: wrist/elbow/shoulder (release angle) and knee/hip (crease momentum)
- **Deferred for MVP** — Speed Gun only needs ball detection

### `tools/` — Shared Utilities
- `download_videos.py` — Download cricket videos via yt-dlp
- `extract_frames.py` — Extract frames at specified FPS

### Testing
- Tests live in `balltracker_trainer/{project}/tests/test_*.py`
- Each script in `scripts/` should have a matching test in `tests/`

---

## CI / CD Rules

### `ci.yml`
- Runs on `push` and `pull_request` to `main`
- Jobs: `test-middleware` (Maven), `test-speedtracking-api` (pytest), `test-compose` (bash)

### `require-tests.yml`
- **Enforces test coverage on PRs**
- If you change `middleware/src/main/java/**/*.java`, you must also change `middleware/src/test/java/**/*.java`
- If you change `speedtracking-api/app/**/*.py`, you must also change `speedtracking-api/tests/test_*.py`
- Same rule applies for `balltracker_trainer/ball-detector/` and `balltracker_trainer/bowler-pose/`

---

## Environment Variables

| Variable | Default | Used By |
|---|---|---|
| `MINIO_ROOT_USER` | `minioadmin` | MinIO, FastAPI, Middleware |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO, FastAPI, Middleware |
| `MINIO_ENDPOINT_URL` | `http://minio:9000` | FastAPI |
| `MINIO_BUCKET` | `deliveries` | FastAPI, Middleware |
| `SPEEDTRACKING_SERVICE_BASE_URL` | `http://localhost:8000` | Middleware |
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://localhost:5432/middleware` | Middleware |

Copy `.env.example` to `.env` for local development. Never commit `.env`.

---

## Docker Compose Dev Stack

```bash
docker compose up --build    # Start all 4 services
docker compose down -v       # Tear down + remove volumes
bash tests/test_compose.sh   # Smoke-test the compose YAML (no containers)
```

Services: `minio` (9000/9001), `minio-init` (bucket setup), `speedtracking-api` (8000), `middleware` (8080)

---

## Delivery Plan (current milestone)

**M3 — Backend Pipeline (in progress):**
- FastAPI: MinIO webhook handler + SSE streaming + async pipeline (bootstrap → real YOLO)
- Middleware: presigned URL upload endpoint + SSE relay endpoint

**Next milestones:**
- M2: Train YOLOv11n ball detector (≥0.7 mAP@50) — gates real inference
- M4: Flutter mobile app (camera → upload → SSE progress → result overlay)
