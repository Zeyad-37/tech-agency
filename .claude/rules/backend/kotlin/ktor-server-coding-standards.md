# Ktor Server Coding Standards

Owner: Link. All Ktor server code MUST follow these standards. For shared KMP code (domain models, DTOs, validation, use cases), see @.claude/rules/mobile/shared/kmp-coding-standards.md — those rules apply here too.

## Why Ktor over Spring

Use Ktor when the backend is part of a Kotlin-first ecosystem where client and server share code via KMP `commonMain`. This enables shared DTOs, validation, error types, and API contracts across Ktor server + Ktor client (Android/iOS/Web). Use Forge (Spring Boot) when Java interop, enterprise Spring ecosystem, or JPA/Hibernate is required.

## Project Structure

```
server/
├── src/main/kotlin/com/example/{project}/
│   ├── Application.kt                    # Ktor application entry point
│   ├── plugins/                           # Ktor plugin configuration
│   │   ├── Routing.kt                     # Route registration
│   │   ├── Serialization.kt              # Content negotiation (JSON)
│   │   ├── Authentication.kt             # JWT / session auth
│   │   ├── StatusPages.kt                # Global error handling
│   │   ├── CORS.kt                        # CORS config
│   │   ├── RateLimit.kt                   # Rate limiting
│   │   └── Monitoring.kt                 # CallLogging, Metrics
│   ├── features/                          # Feature modules (domain-driven)
│   │   └── {feature}/
│   │       ├── routes/
│   │       │   └── {Feature}Routes.kt     # Route definitions (fun Route.featureRoutes())
│   │       ├── service/
│   │       │   └── {Feature}Service.kt    # Business logic
│   │       ├── repository/
│   │       │   └── {Feature}Repository.kt # Database access (Exposed)
│   │       ├── model/
│   │       │   └── {Feature}Table.kt      # Exposed table definitions
│   │       └── di/
│   │           └── {Feature}Module.kt     # Koin module
│   ├── core/
│   │   ├── database/
│   │   │   ├── DatabaseFactory.kt         # HikariCP + Exposed init
│   │   │   └── Migrations.kt             # Flyway or manual migrations
│   │   ├── error/
│   │   │   ├── AppError.kt               # Sealed error hierarchy
│   │   │   └── StatusPagesConfig.kt      # Error → HTTP response mapping
│   │   ├── auth/
│   │   │   ├── JwtConfig.kt              # JWT generation + validation
│   │   │   └── AuthPrincipal.kt          # Custom principal
│   │   ├── di/
│   │   │   └── AppModule.kt              # Core Koin bindings
│   │   └── utils/
│   └── shared/                            # References to KMP shared module
│       └── (imported via Gradle dependency on :shared or :core:domain)
├── src/test/kotlin/com/example/{project}/
│   ├── features/{feature}/
│   │   ├── {Feature}RoutesTest.kt         # Integration tests (TestApplication)
│   │   └── {Feature}ServiceTest.kt        # Unit tests
│   └── TestUtils.kt                       # Test helpers, fixtures
├── build.gradle.kts
└── resources/
    ├── application.conf                   # HOCON config (or application.yaml)
    └── logback.xml                        # Logging config
```

## Layering Rules

Routes → Service → Repository → Database. Never skip layers.

- **Routes** (`fun Route.xxxRoutes()`): HTTP concerns only — receive request, validate, call service, respond. No business logic. No direct database calls.
- **Service**: Business logic, orchestration, authorization checks. Receives typed DTOs/domain objects, returns domain objects. No Ktor `ApplicationCall`, no HTTP concepts.
- **Repository**: Database access only. Encapsulates Exposed queries. Returns domain models. Never returns `ResultRow` to the service.

Dependency direction: Routes → Service → Repository → Exposed/Database. No reverse imports.

## Shared Client-Server Code

The key advantage of Ktor + KMP: shared types between client and server.

```
project/
├── shared/                    # KMP commonMain module
│   └── src/commonMain/kotlin/
│       ├── dto/               # Request/response DTOs — shared by client + server
│       │   ├── CreateNoteRequest.kt
│       │   └── NoteResponse.kt
│       ├── model/             # Domain models
│       ├── validation/        # Shared validation rules
│       └── error/             # Shared error types + response envelope
├── server/                    # Ktor server (depends on :shared)
└── androidApp/                # Android client (depends on :shared)
```

```kotlin
// shared/src/commonMain — used by BOTH client and server
@Serializable
data class CreateNoteRequest(
    @SerialName("title") val title: String,
    @SerialName("content") val content: String,
) {
    fun validate(): List<String> {
        val errors = mutableListOf<String>()
        if (title.isBlank()) errors += "Title is required"
        if (title.length > 200) errors += "Title must be under 200 characters"
        if (content.isBlank()) errors += "Content is required"
        return errors
    }
}

@Serializable
data class NoteResponse(
    @SerialName("id") val id: String,
    @SerialName("title") val title: String,
    @SerialName("content") val content: String,
    @SerialName("created_at") val createdAt: String,
)

// shared/src/commonMain — shared response envelope
@Serializable
data class ApiResponse<T>(
    val status: String,
    val data: T? = null,
    val error: ApiError? = null,
) {
    companion object {
        fun <T> success(data: T) = ApiResponse(status = "success", data = data)
        fun error(code: String, message: String) = ApiResponse<Nothing>(
            status = "error",
            error = ApiError(code, message),
        )
    }
}

@Serializable
data class ApiError(val code: String, val message: String)
```

Rules:
- **Shared DTOs** (`@Serializable`) in KMP `commonMain` — never duplicate between client and server.
- **Shared validation** in `commonMain` — server reuses the same validation the client runs.
- **Shared error envelope** (`ApiResponse<T>`) — consistent shape across all platforms.
- Server imports shared module as a Gradle dependency.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Packages | `lowercase` | `com.example.app.features.notes` |
| Route files | `{Feature}Routes.kt` | `NotesRoutes.kt` |
| Route functions | `fun Route.{feature}Routes()` | `fun Route.notesRoutes()` |
| Services | `{Feature}Service` | `NotesService` |
| Repositories | `{Feature}Repository` | `NotesRepository` |
| Tables (Exposed) | `{Feature}Table`, singular | `NoteTable` |
| Koin modules | `{feature}Module` | `notesModule` |
| Config files | `application.conf` | HOCON format |

## Application Bootstrap

```kotlin
// Application.kt
fun main() {
    embeddedServer(Netty, port = 8080, host = "0.0.0.0") {
        module()
    }.start(wait = true)
}

fun Application.module() {
    // Install plugins
    configureSerialization()
    configureAuthentication()
    configureStatusPages()
    configureCORS()
    configureMonitoring()

    // Initialize DI
    install(Koin) {
        modules(appModule, notesModule, authModule)
    }

    // Initialize database
    DatabaseFactory.init(environment.config)

    // Register routes
    configureRouting()
}
```

- Single `Application.module()` extension that configures everything.
- Each plugin config in its own file under `plugins/`.
- Koin for DI — consistent with KMP modules.
- Database initialized at startup, fail-fast on connection issues.

## Routing

```kotlin
// plugins/Routing.kt
fun Application.configureRouting() {
    val notesService by inject<NotesService>()
    val authService by inject<AuthService>()

    routing {
        route("/api/v1") {
            notesRoutes(notesService)
            authRoutes(authService)
        }
    }
}

// features/notes/routes/NotesRoutes.kt
fun Route.notesRoutes(notesService: NotesService) {
    route("/notes") {
        get {
            val cursor = call.request.queryParameters["cursor"]
            val limit = call.request.queryParameters["limit"]?.toIntOrNull() ?: 20
            val result = notesService.getNotes(cursor, limit)
            call.respond(ApiResponse.success(result))
        }

        post {
            val request = call.receive<CreateNoteRequest>()
            val errors = request.validate() // shared validation from commonMain
            if (errors.isNotEmpty()) {
                throw ValidationException(errors)
            }
            val note = notesService.createNote(request)
            call.respond(HttpStatusCode.Created, ApiResponse.success(note))
        }

        authenticate("jwt") {
            delete("/{id}") {
                val id = call.parameters["id"] ?: throw BadRequestException("Missing id")
                val principal = call.principal<AuthPrincipal>()!!
                notesService.deleteNote(id, principal.userId)
                call.respond(ApiResponse.success(Unit))
            }
        }
    }
}
```

Rules:
- `fun Route.xxxRoutes(service)` — services injected via parameter, not looked up inside routes.
- Route-level `authenticate("jwt") { }` blocks for protected endpoints.
- Use shared `CreateNoteRequest.validate()` from `commonMain`.
- Always respond with `ApiResponse.success(data)` or throw — let StatusPages handle errors.
- Path parameters: `call.parameters["id"]`. Query parameters: `call.request.queryParameters["key"]`.

## Error Handling (StatusPages)

```kotlin
// plugins/StatusPages.kt
fun Application.configureStatusPages() {
    install(StatusPages) {
        exception<AppError.NotFound> { call, cause ->
            call.respond(
                HttpStatusCode.NotFound,
                ApiResponse.error("NOT_FOUND", cause.message ?: "Not found"),
            )
        }
        exception<AppError.Unauthorized> { call, _ ->
            call.respond(
                HttpStatusCode.Unauthorized,
                ApiResponse.error("UNAUTHORIZED", "Authentication required"),
            )
        }
        exception<ValidationException> { call, cause ->
            call.respond(
                HttpStatusCode.UnprocessableEntity,
                ApiResponse.error("VALIDATION_ERROR", cause.errors.joinToString("; ")),
            )
        }
        exception<Throwable> { call, cause ->
            application.log.error("Unhandled exception", cause)
            call.respond(
                HttpStatusCode.InternalServerError,
                ApiResponse.error("INTERNAL_ERROR", "Something went wrong"),
            )
        }
    }
}
```

- Services throw `AppError` subclasses. Routes NEVER catch — let StatusPages handle.
- Never leak stack traces in production responses.
- Log unexpected exceptions at ERROR level with full stack trace.

## Database (Exposed ORM)

```kotlin
// core/database/DatabaseFactory.kt
object DatabaseFactory {
    fun init(config: ApplicationConfig) {
        val url = config.property("database.url").getString()
        val driver = config.property("database.driver").getString()

        val dataSource = HikariDataSource(HikariConfig().apply {
            jdbcUrl = url
            driverClassName = driver
            maximumPoolSize = 10
            isAutoCommit = false
            validate()
        })

        Database.connect(dataSource)

        transaction {
            SchemaUtils.create(NoteTable, UserTable)
        }
    }
}

// features/notes/model/NoteTable.kt
object NoteTable : UUIDTable("notes") {
    val title = varchar("title", 200)
    val content = text("content")
    val authorId = uuid("author_id").references(UserTable.id)
    val createdAt = timestamp("created_at").defaultExpression(CurrentTimestamp)
    val updatedAt = timestamp("updated_at").defaultExpression(CurrentTimestamp)
    val deletedAt = timestamp("deleted_at").nullable()
}

// features/notes/repository/NotesRepository.kt
class NotesRepository {

    suspend fun getAll(cursor: String?, limit: Int): List<NoteResponse> = dbQuery {
        NoteTable
            .selectAll()
            .where { NoteTable.deletedAt.isNull() }
            .orderBy(NoteTable.createdAt, SortOrder.DESC)
            .limit(limit)
            .map { it.toNoteResponse() }
    }

    suspend fun create(request: CreateNoteRequest, authorId: UUID): NoteResponse = dbQuery {
        val id = NoteTable.insertAndGetId {
            it[title] = request.title
            it[content] = request.content
            it[this.authorId] = authorId
        }
        getById(id.value)!!
    }

    private suspend fun <T> dbQuery(block: suspend () -> T): T =
        newSuspendedTransaction(Dispatchers.IO) { block() }
}
```

Rules:
- **Exposed ORM** for all database access. No raw SQL except for complex analytical queries.
- **UUID primary keys** via `UUIDTable`.
- **Timestamps** on every table: `createdAt`, `updatedAt`.
- **Soft deletes**: `deletedAt` nullable column. Filter by `deletedAt.isNull()` in queries.
- **`newSuspendedTransaction(Dispatchers.IO)`** for all DB operations — never block the main coroutine context.
- **HikariCP** connection pool.
- **Flyway** or `SchemaUtils` for migrations. In production, Flyway preferred.

## Dependency Injection (Koin)

```kotlin
// core/di/AppModule.kt
val appModule = module {
    single { DatabaseFactory }
    single { JwtConfig(get()) }
}

// features/notes/di/NotesModule.kt
val notesModule = module {
    single { NotesRepository() }
    single { NotesService(get()) }
}

// All modules aggregated in Application.module()
install(Koin) {
    modules(appModule, notesModule, authModule)
}

// Injecting in routes
val notesService by inject<NotesService>()
```

- Koin for all DI — consistent with KMP modules.
- `single` for stateful services (repositories, services with state).
- `factory` for stateless objects.
- One Koin module per feature.

## Authentication (JWT)

```kotlin
// core/auth/JwtConfig.kt
class JwtConfig(config: ApplicationConfig) {
    private val secret = config.property("jwt.secret").getString()
    private val issuer = config.property("jwt.issuer").getString()
    private val audience = config.property("jwt.audience").getString()
    val realm = config.property("jwt.realm").getString()

    fun generateToken(userId: UUID): String = JWT.create()
        .withAudience(audience)
        .withIssuer(issuer)
        .withClaim("userId", userId.toString())
        .withExpiresAt(Date(System.currentTimeMillis() + 3_600_000)) // 1 hour
        .sign(Algorithm.HMAC256(secret))

    fun configureVerifier(): JWTVerifier = JWT.require(Algorithm.HMAC256(secret))
        .withAudience(audience)
        .withIssuer(issuer)
        .build()
}

// plugins/Authentication.kt
fun Application.configureAuthentication() {
    val jwtConfig by inject<JwtConfig>()

    install(Authentication) {
        jwt("jwt") {
            realm = jwtConfig.realm
            verifier(jwtConfig.configureVerifier())
            validate { credential ->
                val userId = credential.payload.getClaim("userId").asString()
                if (userId != null) AuthPrincipal(UUID.fromString(userId)) else null
            }
        }
    }
}
```

- JWT RS256 or HMAC256 for stateless auth.
- Secrets from config, never hardcoded.
- Custom `AuthPrincipal` data class.
- `authenticate("jwt") { }` blocks on protected route groups.

## Configuration (HOCON)

```hocon
# resources/application.conf
ktor {
    deployment {
        port = 8080
        port = ${?PORT}
    }
    application {
        modules = [com.example.app.ApplicationKt.module]
    }
}

database {
    url = "jdbc:postgresql://localhost:5432/mydb"
    url = ${?DATABASE_URL}
    driver = "org.postgresql.Driver"
}

jwt {
    secret = "dev-secret"
    secret = ${?JWT_SECRET}
    issuer = "my-app"
    audience = "my-app"
    realm = "my-app"
}
```

- HOCON format with environment variable overrides (`${?ENV_VAR}`).
- Defaults for local dev, env vars for production.
- Never commit real secrets — use environment variables.

## Testing

### Test Types & Framework Stack

| Test Type | Framework | Location | Run By |
|-----------|-----------|----------|--------|
| Unit (service) | kotlin.test + Mokkery / Mockito | `src/test/` | CI (every commit) |
| Integration (routes + DB) | Ktor TestApplication + Testcontainers | `src/test/` | CI (every PR) |
| E2E (API flows) | Ktor TestApplication | `src/test/e2e/` | CI (every PR) |
| Load / Stress | k6 | `load-tests/` | CI (pre-release) |
| Security | OWASP dependency-check + detekt | Build plugins | CI (every PR) |
| Contract | Shared KMP DTOs (compile-time) + integration tests | `src/test/` | CI (every commit) |

### Integration Tests — Ktor TestApplication

```kotlin
class NotesRoutesTest {

    @Test
    fun `when POST notes with valid body then returns 201`() = testApplication {
        application {
            configureSerialization()
            configureStatusPages()
            install(Koin) { modules(testModule) }
            routing {
                route("/api/v1") { notesRoutes(get()) }
            }
        }

        val response = client.post("/api/v1/notes") {
            contentType(ContentType.Application.Json)
            setBody("""{"title":"Test","content":"Body"}""")
        }

        assertEquals(HttpStatusCode.Created, response.status)
        val body = response.body<ApiResponse<NoteResponse>>()
        assertEquals("success", body.status)
        assertEquals("Test", body.data?.title)
    }

    @Test
    fun `when POST notes with blank title then returns 422`() = testApplication {
        application {
            configureSerialization()
            configureStatusPages()
            install(Koin) { modules(testModule) }
            routing {
                route("/api/v1") { notesRoutes(get()) }
            }
        }

        val response = client.post("/api/v1/notes") {
            contentType(ContentType.Application.Json)
            setBody("""{"title":"","content":"Body"}""")
        }

        assertEquals(HttpStatusCode.UnprocessableEntity, response.status)
    }

    @Test
    fun `when GET notes then returns paginated list`() = testApplication {
        application {
            configureSerialization()
            configureStatusPages()
            install(Koin) { modules(testModule) }
            routing { route("/api/v1") { notesRoutes(get()) } }
        }

        val response = client.get("/api/v1/notes?limit=10")
        assertEquals(HttpStatusCode.OK, response.status)
    }
}
```

### Unit Tests — Services

```kotlin
class NotesServiceTest {

    private val repository = mock<NotesRepository>()
    private val service = NotesService(repository)

    @Test
    fun `when create note then delegates to repository`() = runTest {
        val request = CreateNoteRequest(title = "Test", content = "Body")
        val expected = NoteResponse(id = "1", title = "Test", content = "Body", createdAt = "2025-01-01T12:00:00")
        whenever(repository.create(request, testUserId)).thenReturn(expected)

        val result = service.createNote(request, testUserId)

        assertEquals(expected, result)
        verify(repository).create(request, testUserId)
    }

    @Test
    fun `when delete note by wrong user then throws Forbidden`() = runTest {
        whenever(repository.getById("1")).thenReturn(NoteResponse(id = "1", title = "T", content = "C", createdAt = "..."))
        whenever(repository.getAuthorId("1")).thenReturn(UUID.randomUUID()) // different user

        assertThrows<AppError.Forbidden> {
            service.deleteNote("1", testUserId)
        }
    }
}
```

### Integration Tests — Database (Testcontainers)

```kotlin
@Testcontainers
class NotesRepositoryDbTest {

    companion object {
        @Container
        val postgres = PostgreSQLContainer("postgres:16-alpine")

        @BeforeAll @JvmStatic
        fun setup() {
            Database.connect(postgres.jdbcUrl, user = postgres.username, password = postgres.password)
            transaction { SchemaUtils.create(NoteTable, UserTable) }
        }
    }

    @Test
    fun `when create and retrieve note then data persists`() = runTest {
        val repo = NotesRepository()
        val created = repo.create(CreateNoteRequest(title = "DB Test", content = "Body"), testUserId)
        val retrieved = repo.getById(created.id)

        assertNotNull(retrieved)
        assertEquals("DB Test", retrieved!!.title)
    }
}
```

### E2E Tests (Full API Flows with Auth)

```kotlin
class AuthLifecycleE2ETest {

    @Test
    fun `complete lifecycle - register, login, create note, delete note`() = testApplication {
        application { module() } // full app config

        // Register
        val register = client.post("/api/v1/auth/register") {
            contentType(ContentType.Application.Json)
            setBody("""{"email":"e2e@test.com","password":"Secure123!","name":"E2E"}""")
        }
        assertEquals(HttpStatusCode.Created, register.status)

        // Login
        val login = client.post("/api/v1/auth/login") {
            contentType(ContentType.Application.Json)
            setBody("""{"email":"e2e@test.com","password":"Secure123!"}""")
        }
        val token = login.body<ApiResponse<AuthTokenResponse>>().data!!.accessToken

        // Create note (authenticated)
        val create = client.post("/api/v1/notes") {
            contentType(ContentType.Application.Json)
            bearerAuth(token)
            setBody("""{"title":"E2E Note","content":"Automated test"}""")
        }
        assertEquals(HttpStatusCode.Created, create.status)
        val noteId = create.body<ApiResponse<NoteResponse>>().data!!.id

        // Delete note (authenticated)
        val delete = client.delete("/api/v1/notes/$noteId") { bearerAuth(token) }
        assertEquals(HttpStatusCode.OK, delete.status)
    }
}
```

### Load / Stress Tests (k6)

```javascript
// load-tests/k6/ktor-notes-load.js
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
  const res = http.get(`${__ENV.BASE_URL}/api/v1/notes?limit=20`);
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
```

### Security Tests

```kotlin
class SecurityTest {

    @Test
    fun `protected endpoints require authentication`() = testApplication {
        application { module() }
        val response = client.delete("/api/v1/notes/1")
        assertEquals(HttpStatusCode.Unauthorized, response.status)
    }

    @Test
    fun `expired JWT is rejected`() = testApplication {
        application { module() }
        val expired = JwtConfig.generateToken(testUserId, expiresIn = (-1).hours)
        val response = client.get("/api/v1/users/me") { bearerAuth(expired) }
        assertEquals(HttpStatusCode.Unauthorized, response.status)
    }

    @Test
    fun `SQL injection in query params handled safely`() = testApplication {
        application { module() }
        val response = client.get("/api/v1/notes?cursor='; DROP TABLE notes; --")
        assertNotEquals(HttpStatusCode.InternalServerError, response.status)
    }

    @Test
    fun `shared validation rejects malicious input`() = testApplication {
        application { module() }
        val response = client.post("/api/v1/notes") {
            contentType(ContentType.Application.Json)
            setBody("""{"title":"<script>alert('xss')</script>","content":"test"}""")
        }
        // Should either sanitize or reject — not store raw script tags
    }
}
```

Build plugin:

```kotlin
// build.gradle.kts
plugins {
    id("org.owasp.dependencycheck")
}
dependencyCheck {
    failBuildOnCVSS = 7.0f
}
```

Rules:
- OWASP dependency-check on every PR. Fail on CVSS >= 7.0.
- Detekt custom rules: no hardcoded secrets, no `!!`, no PII in logs.
- Auth tests: missing token, expired token, wrong user, tampered token.
- Shared validation from `commonMain` tested on both client and server.
- @Shield reviews security tests as part of security review.

### Testing Rules Summary

- **`testApplication { }`** for integration tests — spins up Ktor in-memory, no real server.
- **Mokkery** or **Mockito** for mocking services in unit tests.
- **Testcontainers** for tests that need a real database.
- **Given / When / Then** structure.
- Test naming: `when_x_then_y` or backtick format.
- Coverage: 80%+ services, integration tests for all routes.
- E2E tests: full API lifecycle with auth.
- Load tests pre-release with k6. Security checks on every PR.
- Shared KMP DTOs provide compile-time contract safety between client and server.

## Observability

### Logging

```kotlin
// Structured logging via SLF4J (Ktor uses it natively)
private val logger = LoggerFactory.getLogger(NotesService::class.java)

logger.info("Note created: noteId={}, authorId={}", note.id, authorId)
logger.warn("Validation failed: errors={}", errors)
logger.error("Database error", exception)
```

- **CallLogging plugin** for request/response logging.
- **MDC population** in CallLogging plugin — `traceId`, `userId`, `requestId`.
- **Log sanitization** — strip sensitive fields from logged request/response bodies.
- **JSON format** in production (logstash-logback-encoder), human-readable in dev.
- **Per-module loggers** for filtering.
- Parameterized messages — no string concatenation.
- Never log passwords, tokens, PII beyond user IDs.

### Distributed Tracing

- Auto-instrument via your tracing library's JVM SDK.
- Ktor plugin that extracts `traceparent` from incoming requests and creates server spans.
- Custom spans: wrap Exposed database queries, external HTTP client calls, Koin-managed services.
- Span attributes: `http.method`, `http.route`, `http.status_code`, `db.system`, `db.statement`.
- Trace context propagation in Ktor HttpClient (outgoing requests carry parent trace).

### Metrics

- Custom Ktor plugin or integration that exposes metrics (e.g., `/metrics` endpoint).
- Required metrics: request count/duration/error by route, active connections, response sizes.
- Database metrics: Exposed query count, duration, connection pool stats (HikariCP).
- Business metrics: counters/gauges for domain events.
- Naming convention: `service_metric_name_unit`.

### Health Checks

- `GET /health` — liveness route (returns 200).
- `GET /health/ready` — readiness route (checks database via Exposed, external services).
- Each dependency check with timeout — return 503 with structured failure details.
- Example code for readiness check with Exposed + external API:

```kotlin
fun Application.configureHealthChecks() {
    routing {
        get("/health") {
            call.respondText("OK")
        }

        get("/health/ready") {
            val health = mutableMapOf<String, Any>("status" to "ready", "checks" to mutableMapOf<String, Any>())
            val checks = health["checks"] as MutableMap<String, Any>

            try {
                transaction {
                    exec("SELECT 1")
                }
                checks["database"] = "ok"
            } catch (e: Exception) {
                (health["status"] as String).also { health["status"] = "not_ready" }
                checks["database"] = "failed: ${e.message}"
            }

            try {
                val response = httpClient.get("https://external-api.example.com/health")
                if (response.status.isSuccess()) {
                    checks["external-api"] = "ok"
                } else {
                    health["status"] = "not_ready"
                    checks["external-api"] = "failed: ${response.status}"
                }
            } catch (e: Exception) {
                health["status"] = "not_ready"
                checks["external-api"] = "failed: ${e.message}"
            }

            val statusCode = if (health["status"] == "ready") HttpStatusCode.OK else HttpStatusCode.ServiceUnavailable
            call.respond(statusCode, health)
        }
    }
}
```

### Alerting Integration

- Reference `@.claude/rules/shared/operational-standards.md` for SLO definitions.
- Unhandled exceptions in StatusPages: log at ERROR, report to error tracking service.
- Database connection pool exhaustion: log and alert when pool utilization > 80%.

### Key Rules

- Observability is configured in the Ktor `Application.module()` — install plugins early.
- Share observability patterns with KMP where possible (e.g., same `Logger` interface from `commonMain`).
- Reference `@.claude/rules/mobile/shared/kmp-coding-standards.md` for shared observability interfaces.
- Reference `@.claude/rules/shared/shared-standards.md` for the baseline.

## Security

- Validate ALL inputs at the route boundary (shared validation from `commonMain`).
- Parameterized queries (Exposed handles this).
- Passwords hashed with bcrypt (`jBCrypt`).
- Secrets from env vars, never in code or committed config.
- CORS: explicit origin allowlist, never `anyHost()` in production.
- Rate limiting on public endpoints.
- HTTPS only in production (terminate at reverse proxy).
- Helmet-style security headers via custom plugin.

## Startup & Shutdown

```kotlin
fun main() {
    embeddedServer(Netty, port = 8080, host = "0.0.0.0") {
        module()
    }.start(wait = true)
}

// Graceful shutdown is handled by Ktor/Netty automatically.
// Add shutdown hooks for cleanup:
environment.monitor.subscribe(ApplicationStopping) {
    // Close database pool, flush logs
    DatabaseFactory.close()
}
```

- `embeddedServer` with Netty engine.
- Health check: `GET /health` returning `{"status": "ok"}`.
- Graceful shutdown handled by Ktor. Subscribe to `ApplicationStopping` for cleanup.
- Validate config at startup — fail fast on missing required values.

## Tooling: Kotlin Agent Skills

The **vendored Kotlin Agent Skills** (in `.claude/skills/`) apply to Ktor work too:

- `kotlin-tooling-java-to-kotlin` — converting Java sources to idiomatic Kotlin.
- `kotlin-tooling-agp9-migration` / `kotlin-tooling-cocoapods-spm-migration` — relevant when this Ktor server shares a KMP module with mobile clients (see `kmp-coding-standards.md` "Tooling").

Note: `kotlin-backend-jpa-entity-mapping` targets **Spring Data JPA / Hibernate** and is owned by Forge — it does **not** apply here. Ktor persistence uses **Exposed** (see "Database (Exposed ORM)" above), which has different identity, fetch, and transaction semantics; do not transplant JPA mapping advice onto Exposed tables.

Provenance and full inventory: `.claude/skills/VENDORED-SKILLS.md`. Integration overview: `docs/guides/references/android-kotlin-skills-integration.md`.
