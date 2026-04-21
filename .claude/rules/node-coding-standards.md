# Node.js / Fastify Coding Standards

Owner: Flux. All Node.js backend code MUST follow these standards.

## Project Structure

```
src/
├── config/                # App config, env validation
│   ├── env.ts             # Zod schema validating all env vars at startup
│   └── index.ts           # Typed config export
├── modules/               # Feature modules (domain-driven)
│   └── {module}/
│       ├── {module}.controller.ts   # Fastify route handlers
│       ├── {module}.service.ts      # Business logic
│       ├── {module}.repository.ts   # Prisma data access
│       ├── {module}.schema.ts       # Zod request/response schemas
│       ├── {module}.types.ts        # TypeScript interfaces/types
│       └── __tests__/
│           ├── {module}.service.test.ts
│           └── {module}.controller.test.ts
├── shared/
│   ├── middleware/         # Auth, rate-limit, error handler
│   ├── plugins/           # Fastify plugins (cors, helmet, etc.)
│   ├── errors/            # Custom error classes
│   ├── utils/             # Pure utility functions
│   └── types/             # Shared types/interfaces
├── workers/               # BullMQ job processors
│   └── {job}.worker.ts
├── prisma/
│   ├── schema.prisma
│   └── migrations/
├── app.ts                 # Fastify app factory
└── server.ts              # Entry point, graceful shutdown
```

## Layering Rules

Controller → Service → Repository. Never skip layers.

- **Controller**: HTTP concerns only — parse request, call service, format response. No business logic. No direct Prisma calls.
- **Service**: Business logic, orchestration, validation rules. Receives typed DTOs, returns domain objects. No HTTP concepts (no `req`, `reply`, status codes).
- **Repository**: Data access only. Encapsulates Prisma queries. Returns domain objects, never Prisma-generated types to the service layer. Map Prisma types to domain types here.

Dependency direction: Controller → Service → Repository → Prisma. No reverse imports. No circular dependencies.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files | `kebab-case` or `{module}.{layer}.ts` | `user.service.ts` |
| Classes | `PascalCase` | `UserService` |
| Interfaces | `PascalCase`, no `I` prefix | `UserResponse` (not `IUserResponse`) |
| Functions | `camelCase`, verb-first | `createUser`, `findByEmail` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Env vars | `UPPER_SNAKE_CASE` | `DATABASE_URL` |
| Zod schemas | `camelCase` + `Schema` suffix | `createUserSchema` |
| DB tables | `snake_case`, plural | `user_profiles` |
| DB columns | `snake_case` | `created_at` |

## TypeScript Rules

- `strict: true` in tsconfig — no exceptions.
- No `any`. Use `unknown` + type narrowing when type is truly unknown.
- No type assertions (`as`) except in tests. Use type guards instead.
- All function parameters and return types explicitly typed.
- Prefer `interface` for object shapes, `type` for unions/intersections.
- Use `readonly` on properties that should not be mutated.
- Enums: prefer `as const` objects over TypeScript `enum`.

```typescript
// GOOD
const Status = { ACTIVE: 'active', INACTIVE: 'inactive' } as const;
type Status = (typeof Status)[keyof typeof Status];

// BAD
enum Status { ACTIVE = 'active', INACTIVE = 'inactive' }
```

## Request / Response Validation

Every endpoint MUST have Zod schemas for request body, query params, and path params.

```typescript
// {module}.schema.ts
export const createUserBodySchema = z.object({
  email: z.string().email(),
  name: z.string().min(2).max(100).trim(),
  role: z.enum(['admin', 'member']).default('member'),
});

export const userIdParamSchema = z.object({
  id: z.string().uuid(),
});

export type CreateUserBody = z.infer<typeof createUserBodySchema>;
```

- Derive TypeScript types from Zod schemas (`z.infer<>`), never duplicate.
- Response schemas define the API contract — use them in OpenAPI generation.
- Coerce/transform at the schema level (`.trim()`, `.toLowerCase()`, `.default()`).

## Error Handling

Use a unified error class hierarchy:

```typescript
// shared/errors/app-error.ts
export class AppError extends Error {
  constructor(
    public readonly code: string,
    public readonly statusCode: number,
    message: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = this.constructor.name;
  }
}

export class NotFoundError extends AppError {
  constructor(entity: string, id: string) {
    super('NOT_FOUND', 404, `${entity} with id ${id} not found`);
  }
}

export class ConflictError extends AppError {
  constructor(message: string) {
    super('CONFLICT', 409, message);
  }
}

export class ValidationError extends AppError {
  constructor(details: Record<string, unknown>) {
    super('VALIDATION_ERROR', 422, 'Validation failed', details);
  }
}
```

- Services throw domain errors (e.g., `NotFoundError`). Never throw raw `Error`.
- Controllers NEVER catch errors — let the global error handler plugin handle them.
- Global error handler maps `AppError` to the standard response envelope.
- Log unexpected errors at `error` level, expected errors at `warn`.

## Response Envelope

Every response follows this shape:

```typescript
// Success
{ "status": "success", "data": { ... }, "meta": { "page": "...", "total": 42 } }

// Error
{ "status": "error", "error": { "code": "NOT_FOUND", "message": "...", "details": { ... } } }
```

- `meta` is optional, used for pagination.
- Never return bare arrays — always wrap in `data`.
- Never leak stack traces in production.

## Pagination

Cursor-based by default. Offset-based only when cursor doesn't make sense (e.g., admin dashboards).

```typescript
// Query params schema
const paginationSchema = z.object({
  cursor: z.string().uuid().optional(),
  limit: z.coerce.number().int().min(1).max(100).default(20),
});

// Response meta
interface PaginationMeta {
  nextCursor: string | null;
  hasMore: boolean;
  total?: number; // optional, expensive for large tables
}
```

- Repositories return `{ items, nextCursor, hasMore }`.
- Services pass pagination params through, don't transform them.

## Database / Prisma Patterns

- **No raw SQL.** Use Prisma client for all queries.
- **UUID primary keys** (`@id @default(uuid())`).
- **Timestamps** on every table: `createdAt`, `updatedAt` with `@updatedAt`.
- **Soft deletes**: `deletedAt DateTime?` where business requires it. Add `@index` on `deletedAt`. Repository methods filter by `deletedAt: null` by default.
- **Relations**: Always define both sides. Use `onDelete` explicitly.
- **Indexes**: Add `@@index` for any column used in `WHERE` or `ORDER BY` in queries.
- **Transactions**: Use `prisma.$transaction()` for multi-table writes. Keep transactions short.
- Migrations: one concern per migration file. Name: `YYYYMMDDHHMMSS_short_description`.

## Async Jobs / Queues (BullMQ)

```typescript
// workers/{job}.worker.ts
export const processEmailJob = async (job: Job<EmailJobData>) => {
  // 1. Validate payload
  // 2. Execute (idempotent — check if already done)
  // 3. Return result for logging
};
```

- Every job MUST be idempotent — safe to retry.
- Use deduplication keys to prevent double-processing.
- Set `attempts` + exponential backoff in queue config.
- Configure dead-letter queue (DLQ) for jobs that exhaust retries.
- Job payload: serializable plain objects only, no class instances.
- Log job start/complete/fail with `jobId` and queue name.

## Dependency Injection

Use Fastify's plugin/decorator system or manual factory functions — no DI framework required.

```typescript
// app.ts — register dependencies
app.decorate('userService', new UserService(new UserRepository(prisma)));

// controller — access via app instance
app.get('/users/:id', async (req, reply) => {
  const user = await app.userService.findById(req.params.id);
});
```

- Alternatively, use a simple factory pattern:
  ```typescript
  export function createUserModule(prisma: PrismaClient) {
    const repository = new UserRepository(prisma);
    const service = new UserService(repository);
    const controller = new UserController(service);
    return { controller, service, repository };
  }
  ```
- Services receive repositories via constructor — never import Prisma directly.

## Testing

### Test Types & Framework Stack

| Test Type | Framework | Location | Run By |
|-----------|-----------|----------|--------|
| Unit (service, utils) | Vitest + vi.fn() | `__tests__/*.service.test.ts` | CI (every commit) |
| Integration (controller + DB) | Vitest + Fastify inject + Testcontainers | `__tests__/*.controller.test.ts` | CI (every PR) |
| E2E (API flows) | Vitest + supertest or Fastify inject | `e2e/` | CI (every PR) |
| Load / Stress | k6 | `load-tests/` | CI (pre-release) |
| Security | npm audit + ESLint security + OWASP ZAP | CI pipeline | CI (every PR) |
| Contract | Pact (consumer-driven) | `contract-tests/` | CI (every PR) |

### Unit Tests

```typescript
describe('UserService', () => {
  const mockRepo = { findById: vi.fn(), create: vi.fn() };
  const service = new UserService(mockRepo as unknown as UserRepository);

  it('throws NotFoundError for missing user', async () => {
    mockRepo.findById.mockResolvedValue(null);
    await expect(service.getUser('xyz')).rejects.toThrow(NotFoundError);
  });

  it('creates user and returns domain model', async () => {
    mockRepo.create.mockResolvedValue({ id: '1', email: 'test@example.com', name: 'Test' });
    const user = await service.createUser({ email: 'test@example.com', name: 'Test' });
    expect(user.email).toBe('test@example.com');
    expect(mockRepo.create).toHaveBeenCalledOnce();
  });
});
```

### Integration Tests

```typescript
describe('POST /api/v1/users', () => {
  let app: FastifyInstance;
  beforeAll(async () => { app = await buildApp(); });
  afterAll(async () => { await app.close(); });

  it('creates a user and returns 201', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/v1/users',
      payload: { email: 'test@example.com', name: 'Test User' },
    });
    expect(res.statusCode).toBe(201);
    expect(res.json().data.email).toBe('test@example.com');
  });

  it('returns 422 for invalid email', async () => {
    const res = await app.inject({
      method: 'POST',
      url: '/api/v1/users',
      payload: { email: 'not-an-email', name: 'Test' },
    });
    expect(res.statusCode).toBe(422);
    expect(res.json().error.code).toBe('VALIDATION_ERROR');
  });

  it('returns 409 for duplicate email', async () => {
    await app.inject({ method: 'POST', url: '/api/v1/users', payload: { email: 'dup@test.com', name: 'First' } });
    const res = await app.inject({ method: 'POST', url: '/api/v1/users', payload: { email: 'dup@test.com', name: 'Second' } });
    expect(res.statusCode).toBe(409);
  });
});
```

### E2E Tests (Full API Flows)

```typescript
// e2e/user-lifecycle.test.ts
describe('User lifecycle E2E', () => {
  let app: FastifyInstance;
  let authToken: string;

  beforeAll(async () => { app = await buildApp(); });
  afterAll(async () => { await app.close(); });

  it('complete user lifecycle: register → login → update → delete', async () => {
    // Register
    const register = await app.inject({
      method: 'POST', url: '/api/v1/auth/register',
      payload: { email: 'e2e@test.com', name: 'E2E User', password: 'SecurePass123!' },
    });
    expect(register.statusCode).toBe(201);

    // Login
    const login = await app.inject({
      method: 'POST', url: '/api/v1/auth/login',
      payload: { email: 'e2e@test.com', password: 'SecurePass123!' },
    });
    authToken = login.json().data.token;

    // Update profile
    const update = await app.inject({
      method: 'PATCH', url: '/api/v1/users/me',
      headers: { authorization: `Bearer ${authToken}` },
      payload: { name: 'Updated Name' },
    });
    expect(update.statusCode).toBe(200);
    expect(update.json().data.name).toBe('Updated Name');

    // Delete account
    const del = await app.inject({
      method: 'DELETE', url: '/api/v1/users/me',
      headers: { authorization: `Bearer ${authToken}` },
    });
    expect(del.statusCode).toBe(200);
  });
});
```

### Load / Stress Tests (k6)

```javascript
// load-tests/k6/users-load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 50 },
    { duration: '2m', target: 50 },
    { duration: '30s', target: 200 },
    { duration: '1m', target: 200 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get(`${__ENV.BASE_URL}/api/v1/users?limit=20`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
```

Rules:
- Load tests run against staging before every release.
- Thresholds: P95 < 500ms, P99 < 1000ms, error rate < 1%.
- Include spike tests and soak tests (30+ min sustained load).

### Security Tests

```typescript
describe('Security', () => {
  it('protected endpoints return 401 without token', async () => {
    const res = await app.inject({ method: 'DELETE', url: '/api/v1/users/1' });
    expect(res.statusCode).toBe(401);
  });

  it('expired tokens are rejected', async () => {
    const expiredToken = generateToken({ userId: '1', expiresIn: -1 });
    const res = await app.inject({
      method: 'GET', url: '/api/v1/users/me',
      headers: { authorization: `Bearer ${expiredToken}` },
    });
    expect(res.statusCode).toBe(401);
  });

  it('SQL injection in query params is handled safely', async () => {
    const res = await app.inject({
      method: 'GET',
      url: "/api/v1/users?cursor='; DROP TABLE users; --",
    });
    expect(res.statusCode).not.toBe(500);
  });

  it('rate limiting blocks excessive requests', async () => {
    const requests = Array.from({ length: 110 }, () =>
      app.inject({ method: 'GET', url: '/api/v1/users' }),
    );
    const responses = await Promise.all(requests);
    const rateLimited = responses.filter((r) => r.statusCode === 429);
    expect(rateLimited.length).toBeGreaterThan(0);
  });
});
```

CI pipeline:
- `npm audit --audit-level=high` on every PR — fail on high/critical.
- ESLint `eslint-plugin-security` catches eval, object injection, CSRF patterns.
- OWASP ZAP scan on staging before each release.

### Testing Rules Summary

- Unit tests: mock repository, test service logic in isolation.
- Integration tests: Fastify `inject()` with real DB (Testcontainers or test Postgres).
- E2E tests: full API flow with auth lifecycle.
- Coverage: 80%+ services, 60%+ controllers.
- Test file lives next to source: `__tests__/{module}.service.test.ts`.
- Use `vi.fn()` (Vitest) — no mixing testing libraries.
- Integration tests clean up data (transaction rollback or truncate).
- Load tests pre-release with k6. Security checks on every PR.

## Observability

### Logging

Structured JSON logging via Fastify's built-in Pino logger.

```typescript
// Contextual logging in services
this.logger.info({ userId, action: 'create' }, 'User created');
this.logger.warn({ userId, reason }, 'Duplicate email attempt');
this.logger.error({ err, jobId }, 'Job processing failed');
```

- Always include contextual fields (entity IDs, action).
- Log levels: `error` (unexpected failures), `warn` (expected issues), `info` (state changes), `debug` (verbose, off in prod).
- Never log sensitive data: passwords, tokens, PII beyond user IDs.
- **Correlation**: Inject `requestId` and `traceId` into every log via Fastify request decorator. Reference `shared-standards.md` for the baseline structured JSON schema (`level`, `timestamp`, `service`, `traceId`, `userId`).
- **Sanitization**: Strip sensitive fields (password, token, ssn) from log context automatically.
- **Environment-specific levels**: production=info, staging=debug, development=trace.
- **Child loggers**: Use per-service or per-module child loggers for filtering and context binding.
- Request logging: Fastify auto-logs requests via CallLogging plugin. Log body sanitized for PII.

### Distributed Tracing

- Auto-instrument via your tracing library's Node.js SDK (e.g., OpenTelemetry SDK). Initialize before all other imports in the entry point.
- Propagate trace context via W3C `traceparent` header — Fastify middleware should extract incoming trace and create child spans.
- Custom spans: wrap database queries (Prisma middleware), external HTTP calls, queue operations (BullMQ).
- Span attributes: include `http.method`, `http.route`, `http.status_code`, `db.system`, `db.statement` (sanitized).
- Example: Prisma middleware creating a span per query:

```typescript
// Wrap Prisma queries in spans
prisma.$use(async (params, next) => {
  const tracer = trace.getTracer('prisma');
  const span = tracer.startSpan(`db.${params.action}`, {
    attributes: {
      'db.system': 'postgresql',
      'db.statement': params.args,
    },
  });
  try {
    const result = await next(params);
    span.end();
    return result;
  } catch (e) {
    span.recordException(e);
    span.end();
    throw e;
  }
});
```

### Metrics

- Expose a `/metrics` endpoint (or push to your metrics backend).
- Required metrics: request count (by method, route, status), request duration histogram, active connections gauge, error count (by type).
- Business metrics: custom counters/gauges for domain events (user signups, orders placed, etc.).
- Process metrics: event loop lag, heap usage, GC pauses, active handles.
- Naming convention: `service_name_metric_name_unit` (e.g., `api_http_request_duration_seconds`).

### Health Checks

- `GET /health` — basic liveness (returns 200 if process is running).
- `GET /health/ready` — readiness (checks database connectivity, queue connectivity, external service reachability).
- Each dependency check has a timeout (e.g., 2s) — if any fails, return 503 with details of which dependency is down.
- Example readiness check with Prisma + Redis:

```typescript
app.get('/health/ready', async (request, reply) => {
  const health = { status: 'ready', checks: {} as Record<string, unknown> };
  try {
    // Check database
    await prisma.$queryRaw`SELECT 1`;
    health.checks.database = 'ok';
  } catch (e) {
    health.status = 'not_ready';
    health.checks.database = `failed: ${(e as Error).message}`;
  }

  try {
    // Check Redis
    await redis.ping();
    health.checks.redis = 'ok';
  } catch (e) {
    health.status = 'not_ready';
    health.checks.redis = `failed: ${(e as Error).message}`;
  }

  const statusCode = health.status === 'ready' ? 200 : 503;
  reply.code(statusCode).send(health);
});
```

### Alerting Integration

- Reference `@.claude/rules/operational-standards.md` for SLO definitions and alert thresholds.
- Structured error logging with severity enables alert rules: any ERROR log can trigger an alert in your monitoring platform.
- Unhandled rejections and uncaught exceptions: log at FATAL level, report to your error tracking service, then exit (let the process manager restart).

## Security in Code

- Validate ALL inputs at the boundary (Zod schemas).
- Parameterized queries only (Prisma handles this).
- Hash passwords with `bcrypt` or `argon2` — never store plaintext.
- Environment secrets: never in code, always env vars.
- Set security headers via `@fastify/helmet`.
- Rate limit public endpoints via `@fastify/rate-limit`.
- CORS: explicit origin allowlist, never `*` in production.

## Startup & Shutdown

```typescript
// server.ts
const start = async () => {
  const app = await buildApp();
  await app.listen({ port: config.PORT, host: '0.0.0.0' });

  const shutdown = async (signal: string) => {
    app.log.info({ signal }, 'Shutting down');
    await app.close();        // stops accepting new connections
    await prisma.$disconnect();
    process.exit(0);
  };

  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));
};
```

- Validate env vars before anything else — fail fast.
- Graceful shutdown: drain connections, close DB pool, stop workers.
- Health check endpoint: `GET /health` returning `{ status: "ok" }`.
