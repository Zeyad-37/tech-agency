# Python / FastAPI Coding Standards

Owner: Pyra. All Python backend code MUST follow these standards.

## Project Structure

```
src/
├── config/
│   ├── settings.py        # Pydantic BaseSettings (loads env vars)
│   └── dependencies.py    # FastAPI Depends factories
├── modules/               # Feature modules (domain-driven)
│   └── {module}/
│       ├── __init__.py
│       ├── router.py      # FastAPI router (endpoint definitions)
│       ├── service.py     # Business logic
│       ├── repository.py  # SQLAlchemy data access
│       ├── schemas.py     # Pydantic request/response models
│       ├── models.py      # SQLAlchemy ORM models
│       ├── exceptions.py  # Module-specific errors (optional)
│       └── tests/
│           ├── test_service.py
│           └── test_router.py
├── shared/
│   ├── middleware/         # Auth, CORS, rate limiting
│   ├── errors/            # Base error classes + handlers
│   ├── database.py        # Engine, session factory, Base model
│   ├── pagination.py      # Cursor/offset pagination helpers
│   └── utils/             # Pure utility functions
├── workers/               # Celery tasks
│   └── {task}.py
├── alembic/
│   ├── env.py
│   └── versions/
├── main.py                # FastAPI app factory
└── pyproject.toml
```

## Layering Rules

Router → Service → Repository. Never skip layers.

- **Router**: HTTP concerns only — parse request, call service, format response. No business logic. No direct SQLAlchemy calls. Uses FastAPI `Depends()` for injection.
- **Service**: Business logic, orchestration, domain validation. Receives Pydantic models / typed args, returns domain objects. No HTTP concepts (no `Request`, `Response`, status codes).
- **Repository**: Data access only. Encapsulates SQLAlchemy queries. Returns domain objects or ORM models. Never returns raw `Row` objects to the service layer.

Dependency direction: Router → Service → Repository → SQLAlchemy. No reverse imports. No circular dependencies.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files | `snake_case.py` | `user_service.py` or `service.py` in module dir |
| Classes | `PascalCase` | `UserService` |
| Functions | `snake_case`, verb-first | `create_user`, `find_by_email` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Env vars | `UPPER_SNAKE_CASE` | `DATABASE_URL` |
| Pydantic models | `PascalCase` + purpose suffix | `UserCreateRequest`, `UserResponse` |
| SQLAlchemy models | `PascalCase`, singular | `User`, `UserProfile` |
| DB tables | `snake_case`, plural | `user_profiles` |
| DB columns | `snake_case` | `created_at` |
| Celery tasks | `snake_case` with module prefix | `email.send_welcome_email` |

## Type Hints

- **Every function**: typed parameters and return type. No exceptions.
- Use `from __future__ import annotations` for forward references.
- Use `collections.abc` types over `typing` where possible (`Sequence`, `Mapping`).
- Use `X | None` (union syntax) instead of `Optional[X]`.
- No `Any` except when interfacing with untyped third-party code — add a comment explaining why.

```python
# GOOD
async def find_by_email(self, email: str) -> User | None:
    ...

# BAD
async def find_by_email(self, email):
    ...
```

## Pydantic v2 Patterns

```python
# schemas.py
from pydantic import BaseModel, field_validator, computed_field, ConfigDict

class UserCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    email: str
    name: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        # Custom validation beyond basic type checking
        if not v.strip():
            raise ValueError("Email cannot be blank")
        return v.lower().strip()

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    created_at: datetime

    @computed_field
    @property
    def display_name(self) -> str:
        return self.name.title()
```

- **Request models**: `strict=True`. Use `field_validator` for business rules.
- **Response models**: `from_attributes=True` so `model_validate(orm_instance)` works.
- Never reuse the same model for input and output.
- Split schemas when create vs update have different required fields.

## Error Handling

```python
# shared/errors/app_error.py
class AppError(Exception):
    def __init__(
        self,
        code: str,
        status_code: int,
        message: str,
        details: dict | None = None,
    ):
        self.code = code
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(message)

class NotFoundError(AppError):
    def __init__(self, entity: str, entity_id: str):
        super().__init__("NOT_FOUND", 404, f"{entity} with id {entity_id} not found")

class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__("CONFLICT", 409, message)

class ValidationError(AppError):
    def __init__(self, details: dict):
        super().__init__("VALIDATION_ERROR", 422, "Validation failed", details)
```

- Services throw domain errors. Never raise raw `Exception` or `HTTPException` from services.
- Routers NEVER catch errors — let the global exception handler middleware do it.
- Global handler maps `AppError` subclasses to the standard envelope.
- `HTTPException` only in middleware/auth guards, never in business logic.

## Response Envelope

```python
# shared/schemas.py
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: T
    meta: dict | None = None

class ErrorResponse(BaseModel):
    status: str = "error"
    error: ErrorDetail

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}
```

- Never return bare lists — always wrap in `data`.
- `meta` for pagination metadata.
- Never leak tracebacks in production responses.

## Pagination

Cursor-based by default:

```python
# shared/pagination.py
class CursorPage(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None
    has_more: bool

class PaginationParams(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
```

- Repository returns `CursorPage`. Service passes params through.
- Offset pagination only for admin/dashboard endpoints where random page access is needed.

## Database / SQLAlchemy Patterns

```python
# shared/database.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

# modules/user/models.py
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    deleted_at: Mapped[datetime | None] = mapped_column(default=None, index=True)
```

- **Mapped column annotations** (SQLAlchemy 2.0 style). No legacy `Column()` declarations.
- **UUID primary keys** everywhere.
- **Timestamps** mixin on every model.
- **Soft deletes**: `deleted_at` column where business requires. Repository filters `deleted_at.is_(None)` by default.
- **No raw SQL.** Use SQLAlchemy ORM or `select()` construct.
- **Indexes**: Add for any column in `WHERE`, `ORDER BY`, or `JOIN ON`.
- **Transactions**: Use `async with session.begin()` for multi-table writes. Keep transactions short.
- **Alembic migrations**: One change per file. Autogenerate then review. Name: `{rev}_short_description.py`.

## Async Patterns

- **All I/O must be `async/await`** — DB calls, HTTP calls, file I/O.
- No threaded code. Use `asyncio.to_thread()` only for CPU-bound libraries that have no async variant.
- No `asyncio.gather()` with unbounded lists — use `asyncio.Semaphore` for concurrency limits.
- Use `contextvar` for request-scoped state (e.g., correlation ID), not thread-locals.

```python
# GOOD
async def get_user(self, user_id: str) -> User:
    async with self.session_factory() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

# BAD — blocking call in async context
def get_user(self, user_id: str) -> User:
    return self.session.query(User).get(user_id)
```

## Dependency Injection (FastAPI Depends)

```python
# config/dependencies.py
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

def get_user_repository(session: AsyncSession = Depends(get_session)) -> UserRepository:
    return UserRepository(session)

def get_user_service(repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(repo)

# modules/user/router.py
@router.post("/", response_model=ApiResponse[UserResponse], status_code=201)
async def create_user(
    request: UserCreateRequest,
    service: UserService = Depends(get_user_service),
) -> ApiResponse[UserResponse]:
    user = await service.create_user(request)
    return ApiResponse(data=UserResponse.model_validate(user))
```

- No global state. No module-level singletons.
- Build the dependency chain with `Depends()`.
- Session lifecycle managed by the DI factory, not by service/repository.

## Celery Tasks

```python
# workers/email.py
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def send_welcome_email(self, user_id: str, idempotency_key: str) -> dict:
    if already_processed(idempotency_key):
        return {"status": "skipped", "reason": "duplicate"}
    # ... send email ...
    mark_processed(idempotency_key)
    return {"status": "sent", "user_id": user_id}
```

- Every task MUST be idempotent — safe to retry.
- Use `acks_late=True` for at-least-once delivery.
- `bind=True` for access to `self.retry()`.
- Configure dead-letter queue for exhausted retries.
- Task payload: serializable plain dicts only.
- Log task start/complete/fail with task ID.

## Testing

### Test Types & Framework Stack

| Test Type | Framework | Location | Run By |
|-----------|-----------|----------|--------|
| Unit (service, utils) | pytest + AsyncMock | `modules/{module}/tests/test_service.py` | CI (every commit) |
| Integration (router + DB) | pytest + httpx.AsyncClient + Testcontainers | `modules/{module}/tests/test_router.py` | CI (every PR) |
| E2E (API flows) | pytest + httpx.AsyncClient | `tests/e2e/` | CI (every PR) |
| Load / Stress | k6 or Locust | `load-tests/` | CI (pre-release) |
| Security | pip-audit + Bandit + OWASP ZAP | CI pipeline | CI (every PR) |
| Contract | Schemathesis (OpenAPI fuzzing) | CI pipeline | CI (every PR) |

### Unit Tests

```python
class TestUserService:
    @pytest.fixture
    def mock_repo(self):
        return AsyncMock(spec=UserRepository)

    @pytest.fixture
    def service(self, mock_repo):
        return UserService(mock_repo)

    async def test_create_user_duplicate_raises_conflict(self, service, mock_repo):
        mock_repo.find_by_email.return_value = User(email="taken@test.com")
        with pytest.raises(ConflictError):
            await service.create_user(UserCreateRequest(email="taken@test.com", name="X"))

    async def test_create_user_success(self, service, mock_repo):
        mock_repo.find_by_email.return_value = None
        mock_repo.create.return_value = User(id=uuid4(), email="new@test.com", name="New")
        user = await service.create_user(UserCreateRequest(email="new@test.com", name="New"))
        assert user.email == "new@test.com"
        mock_repo.create.assert_called_once()
```

### Integration Tests

```python
class TestUserRouter:
    async def test_create_user_returns_201(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/users",
            json={"email": "test@example.com", "name": "Test"},
        )
        assert response.status_code == 201
        assert response.json()["data"]["email"] == "test@example.com"

    async def test_create_user_invalid_email_returns_422(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/users",
            json={"email": "not-an-email", "name": "Test"},
        )
        assert response.status_code == 422

    async def test_create_user_duplicate_returns_409(self, client: AsyncClient):
        await client.post("/api/v1/users", json={"email": "dup@test.com", "name": "First"})
        response = await client.post("/api/v1/users", json={"email": "dup@test.com", "name": "Second"})
        assert response.status_code == 409
```

### E2E Tests (Full API Flows)

```python
# tests/e2e/test_user_lifecycle.py
class TestUserLifecycle:
    async def test_register_login_update_delete(self, client: AsyncClient):
        # Register
        reg = await client.post("/api/v1/auth/register", json={
            "email": "e2e@test.com", "name": "E2E User", "password": "SecurePass123!"
        })
        assert reg.status_code == 201

        # Login
        login = await client.post("/api/v1/auth/login", json={
            "email": "e2e@test.com", "password": "SecurePass123!"
        })
        token = login.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Update
        update = await client.patch("/api/v1/users/me", json={"name": "Updated"}, headers=headers)
        assert update.status_code == 200
        assert update.json()["data"]["name"] == "Updated"

        # Delete
        delete = await client.delete("/api/v1/users/me", headers=headers)
        assert delete.status_code == 200
```

### Load / Stress Tests (Locust or k6)

```python
# load-tests/locustfile.py
from locust import HttpUser, task, between

class ApiUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_users(self):
        self.client.get("/api/v1/users?limit=20")

    @task(1)
    def create_user(self):
        self.client.post("/api/v1/users", json={
            "email": f"load-{time.time()}@test.com",
            "name": "Load Test User",
        })
```

Rules:
- Load tests run against staging before every release.
- Thresholds: P95 < 500ms, P99 < 1000ms, error rate < 1%.
- Locust for Python-native load testing, k6 as alternative.

### Security Tests

```python
class TestSecurity:
    async def test_protected_endpoint_requires_auth(self, client: AsyncClient):
        response = await client.delete("/api/v1/users/1")
        assert response.status_code == 401

    async def test_expired_token_rejected(self, client: AsyncClient):
        expired = generate_token(user_id="1", expires_delta=timedelta(seconds=-1))
        response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {expired}"})
        assert response.status_code == 401

    async def test_sql_injection_handled(self, client: AsyncClient):
        response = await client.get("/api/v1/users?cursor='; DROP TABLE users; --")
        assert response.status_code != 500

    async def test_rate_limiting(self, client: AsyncClient):
        responses = [await client.get("/api/v1/users") for _ in range(110)]
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0
```

CI pipeline:
- `pip-audit` on every PR — fail on known vulnerabilities.
- `bandit -r src/` for Python-specific security lint (hardcoded passwords, eval, etc.).
- OWASP ZAP scan on staging before each release.
- Schemathesis: auto-generate test cases from OpenAPI spec to fuzz endpoints.

### Testing Rules Summary

- `pytest` + `pytest-asyncio` for all tests. No `unittest.TestCase`.
- Fixtures for test data factories. Use `factory_boy` for complex models.
- Integration tests use real DB, clean up with transaction rollback.
- E2E tests cover complete API flows with authentication.
- Coverage: 80%+ services, 60%+ routers.
- Load tests pre-release. Security checks on every PR.

## Observability

### Logging

Structured JSON logging via `structlog`:

```python
import structlog
logger = structlog.get_logger()

# In service
logger.info("user_created", user_id=str(user.id), email=user.email)
logger.warning("duplicate_email_attempt", email=email)
logger.error("job_failed", job_id=job_id, exc_info=True)
```

- Always include contextual fields (entity IDs, action name).
- Log levels: `error` (unexpected), `warn` (expected issues), `info` (state changes), `debug` (verbose, off in prod).
- Never log passwords, tokens, PII beyond user IDs.
- **Correlation**: Middleware that binds `request_id`, `trace_id`, `user_id` to structlog context on every request. Reference `shared-standards.md` for the baseline structured JSON schema.
- **Sanitization**: Log sanitization processor — strip sensitive fields automatically.
- **Formatting**: JSON renderer in production, colored console in development.
- **Per-module loggers**: Use `structlog.get_logger(__name__)` for per-module logger instances.

### Distributed Tracing

- Auto-instrument via your tracing library's Python SDK (e.g., OpenTelemetry SDK). Initialize in app startup/lifespan.
- Propagate W3C `traceparent` header — FastAPI middleware extracts incoming trace context.
- Custom spans: wrap database queries (SQLAlchemy event hooks), external HTTP calls (`httpx`), Celery tasks.
- Span attributes: `http.method`, `http.route`, `http.status_code`, `db.system`, `db.statement` (sanitized).
- Example: SQLAlchemy event listener creating a span per query:

```python
from sqlalchemy import event
from opentelemetry import trace

tracer = trace.get_tracer("sqlalchemy")

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())
    span = tracer.start_span(
        f"db.query",
        attributes={
            "db.system": "postgresql",
            "db.statement": statement,
        },
    )
    conn.info['current_span'] = span

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    span = conn.info.get('current_span')
    if span:
        span.end()
```

### Metrics

- Expose `/metrics` endpoint or push to your metrics backend.
- Required metrics: request count (by method, route, status), request duration histogram, active connections, error count.
- Business metrics: custom counters/gauges for domain events.
- Process metrics: Python-specific — GC collections, thread count, memory RSS.
- Naming convention: `service_name_metric_name_unit`.

### Health Checks

- `GET /health` — liveness.
- `GET /health/ready` — readiness (check database, Redis, Celery broker, external APIs).
- Each dependency check with timeout — return 503 with details on failure.
- Example readiness check with SQLAlchemy + Redis:

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health/ready")
async def readiness():
    health = {"status": "ready", "checks": {}}

    try:
        async with get_db() as session:
            await session.execute(select(1))
        health["checks"]["database"] = "ok"
    except Exception as e:
        health["status"] = "not_ready"
        health["checks"]["database"] = f"failed: {str(e)}"

    try:
        await redis_client.ping()
        health["checks"]["redis"] = "ok"
    except Exception as e:
        health["status"] = "not_ready"
        health["checks"]["redis"] = f"failed: {str(e)}"

    status_code = 200 if health["status"] == "ready" else 503
    return JSONResponse(content=health, status_code=status_code)
```

### Alerting Integration

- Reference `@.claude/rules/operational-standards.md` for SLO definitions.
- Unhandled exceptions: log at CRITICAL, report to error tracking, return 500 structured response.
- Celery task failures: log with task ID, queue name, retry count — enable alerting on repeated failures.

## Security in Code

- Validate ALL inputs at the boundary (Pydantic schemas).
- Parameterized queries only (SQLAlchemy handles this).
- Hash passwords with `bcrypt` or `argon2` via `passlib`.
- Secrets: env vars only, loaded through Pydantic `BaseSettings`.
- CORS: explicit origin list via `CORSMiddleware`, never `allow_origins=["*"]` in prod.
- Rate limiting via `slowapi` or reverse proxy.
- Security headers via middleware.

## Startup & Shutdown

```python
# main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()  # validates env vars — fail fast
    await init_db()
    yield
    # Shutdown
    await dispose_engine()

app = FastAPI(lifespan=lifespan)
```

- Validate settings at startup — fail fast on missing env vars.
- Health check: `GET /health` returning `{"status": "ok"}`.
- Graceful shutdown: drain connections, close DB pool, stop Celery workers.
