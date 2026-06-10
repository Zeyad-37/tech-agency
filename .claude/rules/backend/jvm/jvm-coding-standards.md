# JVM / Spring Boot Coding Standards

Owner: Forge. All Spring Boot / JVM backend code MUST follow these standards. For Kotlin-first backends that share code with KMP clients via Ktor, see @.claude/rules/backend/kotlin/ktor-server-coding-standards.md (owned by Link).

## Project Structure

```
src/
├── main/
│   ├── kotlin (or java)/
│   │   └── com/example/{project}/
│   │       ├── config/                # Spring @Configuration classes
│   │       │   ├── SecurityConfig.kt
│   │       │   ├── WebConfig.kt
│   │       │   └── ResilienceConfig.kt
│   │       ├── modules/               # Feature modules (domain-driven)
│   │       │   └── {module}/
│   │       │       ├── {Module}Controller.kt
│   │       │       ├── {Module}Service.kt
│   │       │       ├── {Module}Repository.kt
│   │       │       ├── {Module}Entity.kt        # JPA entity
│   │       │       ├── dto/
│   │       │       │   ├── {Module}Request.kt    # Incoming DTOs
│   │       │       │   └── {Module}Response.kt   # Outgoing DTOs
│   │       │       └── exception/                # Module-specific exceptions (optional)
│   │       ├── shared/
│   │       │   ├── error/             # Global exception handler + error classes
│   │       │   ├── pagination/        # Cursor pagination utilities
│   │       │   ├── security/          # JWT filters, auth utilities
│   │       │   └── util/              # Pure utility classes
│   │       └── Application.kt        # @SpringBootApplication entry point
│   └── resources/
│       ├── application.yml
│       ├── application-{profile}.yml
│       └── db/migration/              # Flyway migrations
│           └── V{version}__{description}.sql
└── test/
    └── kotlin (or java)/
        └── com/example/{project}/
            └── modules/{module}/
                ├── {Module}ServiceTest.kt
                └── {Module}ControllerIntegrationTest.kt
```

## Layering Rules

Controller → Service → Repository. Never skip layers.

- **Controller**: HTTP concerns only — validate request (`@Valid`), call service, map to response DTO. No business logic. No direct repository calls. No entity references.
- **Service**: Business logic, orchestration, transaction boundaries (`@Transactional`). Receives command/query objects or DTOs, returns domain objects. No HTTP concepts (no `HttpServletRequest`, no `ResponseEntity` construction).
- **Repository**: Data access only. Extends `JpaRepository` or `CrudRepository`. Custom queries via `@Query` or Specifications/Criteria API. Returns entities.

Dependency direction: Controller → Service → Repository → JPA/JDBC. No reverse imports. No circular dependencies.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Packages | `lowercase`, dot-separated | `com.example.myapp.modules.user` |
| Classes | `PascalCase` + layer suffix | `UserService`, `UserController` |
| Interfaces | `PascalCase`, no `I` prefix | `UserRepository` (not `IUserRepository`) |
| Methods | `camelCase`, verb-first | `createUser`, `findByEmail` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| DTOs | `PascalCase` + `Request`/`Response` | `CreateUserRequest`, `UserResponse` |
| Entities | `PascalCase`, singular | `User`, `UserProfile` |
| DB tables | `snake_case`, plural | `user_profiles` |
| DB columns | `snake_case` | `created_at` |
| Flyway scripts | `V{n}__{description}.sql` | `V3__add_user_profiles_table.sql` |

## Kotlin Conventions (preferred language)

- Prefer Kotlin over Java for new code. Java 21+ when Kotlin is not an option.
- When converting existing `.java` files to Kotlin, invoke the `kotlin-tooling-java-to-kotlin` skill first (see @.claude/rules/shared/kotlin-agent-skills.md) — it handles framework-aware conversion (Spring, Lombok, Hibernate, JUnit, Mockito).
- Use `data class` for DTOs and value objects.
- Use `val` (immutable) by default; `var` only when mutation is required.
- Use `?.let {}`, `?:`, `?.` for null handling — no manual null checks.
- Extension functions for utility logic on existing types.
- Coroutines: use only when the project uses WebFlux. Stick to imperative for Spring MVC.
- No `!!` (not-null assertion) — redesign to eliminate nulls or use safe handling.

```kotlin
// GOOD — data class DTO
data class CreateUserRequest(
    @field:NotBlank val email: String,
    @field:Size(min = 2, max = 100) val name: String,
)

// GOOD — null-safe handling
fun findDisplayName(user: User?): String =
    user?.profile?.displayName ?: "Anonymous"

// BAD — not-null assertion
val name = user!!.name
```

## Request / Response Validation

Use Bean Validation (Jakarta Validation) annotations on request DTOs:

```kotlin
data class CreateUserRequest(
    @field:NotBlank
    @field:Email
    val email: String,

    @field:NotBlank
    @field:Size(min = 2, max = 100)
    val name: String,

    @field:NotNull
    val role: UserRole = UserRole.MEMBER,
)
```

- Always `@Valid` on controller method parameters.
- Custom validators via `@Constraint` + `ConstraintValidator` for complex rules.
- Never validate in the service layer what Bean Validation can handle at the boundary.
- Response DTOs: no validation annotations. Factory method `from(entity)` for mapping.

```kotlin
data class UserResponse(
    val id: UUID,
    val email: String,
    val name: String,
    val createdAt: Instant,
) {
    companion object {
        fun from(user: User): UserResponse = UserResponse(
            id = user.id,
            email = user.email,
            name = user.name,
            createdAt = user.createdAt,
        )
    }
}
```

## Error Handling

```kotlin
// shared/error/AppException.kt
sealed class AppException(
    val code: String,
    val statusCode: Int,
    override val message: String,
    val details: Map<String, Any> = emptyMap(),
) : RuntimeException(message)

class NotFoundException(entity: String, id: String) :
    AppException("NOT_FOUND", 404, "$entity with id $id not found")

class ConflictException(message: String) :
    AppException("CONFLICT", 409, message)

class BusinessValidationException(details: Map<String, Any>) :
    AppException("VALIDATION_ERROR", 422, "Validation failed", details)
```

Global exception handler:

```kotlin
@RestControllerAdvice
class GlobalExceptionHandler {

    @ExceptionHandler(AppException::class)
    fun handleAppException(ex: AppException): ResponseEntity<ErrorResponse> =
        ResponseEntity.status(ex.statusCode).body(
            ErrorResponse(
                status = "error",
                error = ErrorDetail(code = ex.code, message = ex.message, details = ex.details),
            )
        )

    @ExceptionHandler(MethodArgumentNotValidException::class)
    fun handleValidation(ex: MethodArgumentNotValidException): ResponseEntity<ErrorResponse> {
        val details = ex.bindingResult.fieldErrors.associate { it.field to (it.defaultMessage ?: "invalid") }
        return ResponseEntity.unprocessableEntity().body(
            ErrorResponse(status = "error", error = ErrorDetail("VALIDATION_ERROR", "Validation failed", details))
        )
    }
}
```

- Services throw `AppException` subclasses. Never throw raw `RuntimeException`.
- Controllers NEVER catch exceptions — let `@RestControllerAdvice` handle them.
- Log unexpected exceptions at `ERROR`, business exceptions at `WARN`.

## Response Envelope

```kotlin
data class ApiResponse<T>(
    val status: String = "success",
    val data: T,
    val meta: Map<String, Any>? = null,
)

data class ErrorResponse(
    val status: String = "error",
    val error: ErrorDetail,
)

data class ErrorDetail(
    val code: String,
    val message: String,
    val details: Map<String, Any> = emptyMap(),
)
```

- Never return bare lists — always wrap in `data`.
- `meta` for pagination info.
- Never leak stack traces in production responses.

## Pagination

Cursor-based by default:

```kotlin
data class CursorPage<T>(
    val items: List<T>,
    val nextCursor: String?,
    val hasMore: Boolean,
)

data class PaginationParams(
    val cursor: String? = null,
    @field:Min(1) @field:Max(100)
    val limit: Int = 20,
)
```

- Repository builds cursor queries. Service passes params through.
- Use Spring Data `Pageable` only for admin/dashboard offset pagination.

## JPA Entity Patterns

Before creating or reviewing JPA entities, or diagnosing N+1 / `LazyInitializationException` issues, invoke the JetBrains `kotlin-backend-jpa-entity-mapping` skill (see @.claude/rules/shared/kotlin-agent-skills.md). The patterns below are the project baseline; the skill governs the Kotlin-specific ORM mechanics.

```kotlin
@Entity
@Table(name = "users")
class User(
    @Id
    val id: UUID = UUID.randomUUID(),

    @Column(nullable = false, unique = true, length = 255)
    var email: String,

    @Column(nullable = false, length = 100)
    var name: String,

    @Column(name = "deleted_at")
    var deletedAt: Instant? = null,

    @Column(name = "created_at", nullable = false, updatable = false)
    val createdAt: Instant = Instant.now(),

    @Column(name = "updated_at", nullable = false)
    var updatedAt: Instant = Instant.now(),
) {
    // Business-key equals/hashCode — NEVER use @Id
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is User) return false
        return email == other.email
    }

    override fun hashCode(): Int = email.hashCode()
}
```

- **UUID primary keys** — no auto-increment.
- **Timestamps** on every entity: `createdAt`, `updatedAt`.
- **equals/hashCode on business key** (e.g., email, natural ID) — NEVER on `@Id`. This is critical for JPA identity in Sets and detached entities.
- **Soft deletes**: `deletedAt` field + `@Where(clause = "deleted_at IS NULL")` or repository method filtering.
- **No Lombok** in Kotlin projects. In Java projects, use Lombok sparingly (only `@Getter`, `@Builder`, `@RequiredArgsConstructor`).
- **Lazy loading by default** for `@OneToMany` / `@ManyToMany`. Use `JOIN FETCH` in queries when needed.
- **No cascade ALL** — be explicit about cascade types.

## Database Migrations (Flyway)

- **One change per migration file.** Don't mix table creation with data migration.
- **Naming**: `V{version}__{description}.sql` (double underscore). Version is sequential integer.
- **Reversible**: Every migration should be paired with a rollback strategy (documented in comments at the top of the file).
- **Expand-and-contract** for breaking changes: add new column → migrate data → drop old column (separate migrations).
- **Never modify** a migration that has been applied to any environment.
- **Indexes**: Add for FK columns, `WHERE`/`ORDER BY` columns, unique constraints.

```sql
-- V3__add_user_profiles_table.sql
-- Rollback: DROP TABLE IF EXISTS user_profiles;

CREATE TABLE user_profiles (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bio        TEXT,
    avatar_url VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
```

## Dependency Injection

- Constructor injection only. No `@Autowired` on fields.
- Kotlin: single-constructor classes are auto-injected (no `@Autowired` needed).
- Use `@Configuration` + `@Bean` for third-party objects.
- Profile-specific beans via `@Profile("prod")` / `@Profile("test")`.

```kotlin
// GOOD — constructor injection (auto-wired in Kotlin)
@Service
class UserService(
    private val userRepository: UserRepository,
    private val eventPublisher: ApplicationEventPublisher,
)

// BAD — field injection
@Service
class UserService {
    @Autowired
    private lateinit var userRepository: UserRepository
}
```

## Transaction Management

- `@Transactional` on service methods, not on controllers or repositories.
- Read-only operations: `@Transactional(readOnly = true)`.
- Keep transactions short — no external HTTP calls inside a transaction.
- Explicit rollback rules: `@Transactional(rollbackFor = [Exception::class])`.

```kotlin
@Service
class UserService(private val userRepository: UserRepository) {

    @Transactional
    fun createUser(request: CreateUserRequest): User {
        if (userRepository.existsByEmail(request.email)) {
            throw ConflictException("Email ${request.email} already registered")
        }
        return userRepository.save(User(email = request.email, name = request.name))
    }

    @Transactional(readOnly = true)
    fun findById(id: UUID): User =
        userRepository.findByIdOrNull(id) ?: throw NotFoundException("User", id.toString())
}
```

## Resilience Patterns

Use `resilience4j` for external service calls:

```kotlin
@CircuitBreaker(name = "paymentService", fallbackMethod = "paymentFallback")
@Retry(name = "paymentService")
@TimeLimiter(name = "paymentService")
fun processPayment(request: PaymentRequest): PaymentResult { ... }

fun paymentFallback(request: PaymentRequest, ex: Throwable): PaymentResult {
    logger.warn("Payment service unavailable, queuing for retry", ex)
    return PaymentResult.QUEUED
}
```

- **Circuit breakers** on all external HTTP calls.
- **Retry** with exponential backoff for transient failures.
- **Time limiter** to prevent hanging calls.
- **Bulkhead** for thread pool isolation on critical paths.
- Configure in `application.yml`, not in code.

## Testing

### Test Types & Framework Stack

| Test Type | Framework | Location | Run By |
|-----------|-----------|----------|--------|
| Unit (service) | JUnit 5 + MockK / Mockito | `src/test/` | CI (every commit) |
| Integration (controller + DB) | @SpringBootTest + @Testcontainers | `src/test/` | CI (every PR) |
| Test slices | @WebMvcTest, @DataJpaTest | `src/test/` | CI (every commit) |
| E2E (API flows) | JUnit 5 + TestRestTemplate | `src/test/e2e/` | CI (every PR) |
| Load / Stress | k6 or Gatling | `load-tests/` | CI (pre-release) |
| Security | OWASP dependency-check + SpotBugs | Build plugins | CI (every PR) |
| Contract | Spring Cloud Contract or Pact | `src/test/contracts/` | CI (every PR) |

### Unit Tests (MockK)

```kotlin
class UserServiceTest {
    private val userRepository = mockk<UserRepository>()
    private val service = UserService(userRepository)

    @Test
    fun `createUser throws ConflictException for duplicate email`() {
        every { userRepository.existsByEmail("taken@test.com") } returns true

        assertThrows<ConflictException> {
            service.createUser(CreateUserRequest(email = "taken@test.com", name = "Test"))
        }
    }

    @Test
    fun `createUser saves and returns user`() {
        every { userRepository.existsByEmail(any()) } returns false
        every { userRepository.save(any()) } answers { firstArg() }

        val user = service.createUser(CreateUserRequest(email = "new@test.com", name = "New"))
        assertEquals("new@test.com", user.email)
        verify(exactly = 1) { userRepository.save(any()) }
    }
}
```

### Integration Tests (@Testcontainers)

```kotlin
@SpringBootTest(webEnvironment = RANDOM_PORT)
@Testcontainers
class UserControllerIntegrationTest {

    @Container
    companion object {
        val postgres = PostgreSQLContainer("postgres:16-alpine")
    }

    @Autowired
    lateinit var restTemplate: TestRestTemplate

    @Test
    fun `POST users returns 201`() {
        val response = restTemplate.postForEntity(
            "/api/v1/users",
            CreateUserRequest(email = "test@example.com", name = "Test"),
            ApiResponse::class.java,
        )
        assertThat(response.statusCode).isEqualTo(HttpStatus.CREATED)
    }

    @Test
    fun `POST users with invalid email returns 422`() {
        val response = restTemplate.postForEntity(
            "/api/v1/users",
            CreateUserRequest(email = "bad", name = "Test"),
            ErrorResponse::class.java,
        )
        assertThat(response.statusCode).isEqualTo(HttpStatus.UNPROCESSABLE_ENTITY)
    }

    @Test
    fun `POST users duplicate email returns 409`() {
        restTemplate.postForEntity("/api/v1/users", CreateUserRequest(email = "dup@test.com", name = "First"), ApiResponse::class.java)
        val response = restTemplate.postForEntity("/api/v1/users", CreateUserRequest(email = "dup@test.com", name = "Second"), ErrorResponse::class.java)
        assertThat(response.statusCode).isEqualTo(HttpStatus.CONFLICT)
    }
}
```

### Test Slices

```kotlin
// Controller-only (no DB, no service)
@WebMvcTest(UserController::class)
class UserControllerSliceTest {
    @Autowired lateinit var mockMvc: MockMvc
    @MockkBean lateinit var userService: UserService

    @Test
    fun `GET users returns 200`() {
        every { userService.findAll(any()) } returns CursorPage(items = emptyList(), nextCursor = null, hasMore = false)
        mockMvc.get("/api/v1/users").andExpect { status { isOk() } }
    }
}

// Repository-only (real DB, no web layer)
@DataJpaTest
@Testcontainers
class UserRepositoryTest {
    @Container companion object { val postgres = PostgreSQLContainer("postgres:16-alpine") }
    @Autowired lateinit var userRepository: UserRepository

    @Test
    fun `findByEmail returns user when exists`() {
        userRepository.save(User(email = "test@test.com", name = "Test"))
        val found = userRepository.findByEmail("test@test.com")
        assertThat(found).isNotNull
        assertThat(found!!.name).isEqualTo("Test")
    }
}
```

### E2E Tests (Full API Flows)

```kotlin
@SpringBootTest(webEnvironment = RANDOM_PORT)
@Testcontainers
class UserLifecycleE2ETest {

    @Container companion object { val postgres = PostgreSQLContainer("postgres:16-alpine") }
    @Autowired lateinit var restTemplate: TestRestTemplate

    @Test
    fun `complete user lifecycle - register, login, update, delete`() {
        // Register
        val register = restTemplate.postForEntity("/api/v1/auth/register",
            RegisterRequest(email = "e2e@test.com", name = "E2E", password = "Secure123!"), ApiResponse::class.java)
        assertThat(register.statusCode).isEqualTo(HttpStatus.CREATED)

        // Login
        val login = restTemplate.postForEntity("/api/v1/auth/login",
            LoginRequest(email = "e2e@test.com", password = "Secure123!"), ApiResponse::class.java)
        val token = (login.body!!.data as Map<*, *>)["token"] as String

        // Update
        val headers = HttpHeaders().apply { setBearerAuth(token) }
        val update = restTemplate.exchange("/api/v1/users/me", HttpMethod.PATCH,
            HttpEntity(UpdateUserRequest(name = "Updated"), headers), ApiResponse::class.java)
        assertThat(update.statusCode).isEqualTo(HttpStatus.OK)

        // Delete
        val delete = restTemplate.exchange("/api/v1/users/me", HttpMethod.DELETE,
            HttpEntity<Void>(headers), ApiResponse::class.java)
        assertThat(delete.statusCode).isEqualTo(HttpStatus.OK)
    }
}
```

### Load / Stress Tests (Gatling or k6)

```kotlin
// Gatling simulation (Kotlin DSL)
class UserApiSimulation : Simulation() {
    val httpProtocol = http.baseUrl("http://localhost:8080")

    val listUsers = scenario("List Users").exec(
        http("GET /users").get("/api/v1/users?limit=20")
            .check(status().`is`(200))
    )

    init {
        setUp(
            listUsers.inject(
                rampUsers(50).during(30),
                constantUsersPerSec(50.0).during(120),
                rampUsers(200).during(30),
            )
        ).protocols(httpProtocol)
         .assertions(
             global().responseTime().percentile3().lt(500),  // P95 < 500ms
             global().responseTime().percentile4().lt(1000), // P99 < 1000ms
             global().failedRequests().percent().lt(1.0),
         )
    }
}
```

Rules:
- Load tests run against staging before every release.
- Gatling for JVM-native load testing, k6 as alternative.
- Thresholds: P95 < 500ms, P99 < 1000ms, error rate < 1%.

### Security Tests

```kotlin
class SecurityTest {

    @Test
    fun `protected endpoints require authentication`() {
        val response = restTemplate.delete("/api/v1/users/1")
        assertThat(response.statusCode).isEqualTo(HttpStatus.UNAUTHORIZED)
    }

    @Test
    fun `expired JWT is rejected`() {
        val expiredToken = jwtService.generateToken(testUserId, expiresIn = Duration.ofSeconds(-1))
        val headers = HttpHeaders().apply { setBearerAuth(expiredToken) }
        val response = restTemplate.exchange("/api/v1/users/me", HttpMethod.GET,
            HttpEntity<Void>(headers), ErrorResponse::class.java)
        assertThat(response.statusCode).isEqualTo(HttpStatus.UNAUTHORIZED)
    }

    @Test
    fun `SQL injection in query params handled safely`() {
        val response = restTemplate.getForEntity("/api/v1/users?cursor='; DROP TABLE users; --", ErrorResponse::class.java)
        assertThat(response.statusCode).isNotEqualTo(HttpStatus.INTERNAL_SERVER_ERROR)
    }
}
```

Build plugin:

```kotlin
// build.gradle.kts
plugins {
    id("org.owasp.dependencycheck") version "10.0.0"
}

dependencyCheck {
    failBuildOnCVSS = 7.0f
    suppressionFile = "config/owasp-suppressions.xml"
}
```

Rules:
- OWASP dependency-check on every PR. Fail on CVSS >= 7.0.
- SpotBugs for static analysis (SQL injection, XSS, hardcoded credentials).
- Auth tests: missing token, expired token, wrong role, tampered token.
- @Shield reviews security tests as part of security review.

### Testing Rules Summary

- Use `MockK` for Kotlin, `Mockito` for Java.
- `@Testcontainers` for real DB in integration tests.
- `@DirtiesContext` only when absolutely necessary — prefer transaction rollback.
- Test slices: `@WebMvcTest` for controller-only, `@DataJpaTest` for repository-only.
- E2E tests: full API lifecycle with real DB and auth.
- Coverage: 80%+ services, 60%+ controllers.
- Load tests pre-release with Gatling/k6. Security checks on every PR.

## Observability

### Logging

Structured logging via SLF4J + Logback (JSON in production):

```kotlin
private val logger = LoggerFactory.getLogger(UserService::class.java)

// In service
logger.info("User created: userId={}, email={}", user.id, user.email)
logger.warn("Duplicate email attempt: email={}", email)
logger.error("Payment processing failed: orderId={}", orderId, exception)
```

- Use parameterized messages `{}` — never string concatenation.
- **MDC filter** that populates `traceId`, `spanId`, `userId`, `requestId` from incoming headers.
- **Log sanitization** — custom Logback layout that masks sensitive fields.
- **Async logging** in production (Logback AsyncAppender) to avoid blocking request threads.
- **Correlation** between logs and traces — include `traceId` in every log line automatically via MDC.
- Log levels: `ERROR` (unexpected), `WARN` (expected issues), `INFO` (state changes), `DEBUG` (verbose, off in prod).
- Never log passwords, tokens, PII beyond user IDs.
- JSON format in production (`logstash-logback-encoder`), human-readable in dev.

### Distributed Tracing

- Auto-instrumentation via your tracing agent/SDK (Java agent or library initialization).
- Custom spans: annotate critical methods with `@Observed` or create spans programmatically.
- Span attributes: `http.method`, `http.route`, `http.status_code`, `db.system`, `db.statement`.
- Database: auto-instrument JPA/Hibernate queries, connection pool metrics.
- Messaging: auto-instrument message producers/consumers (trace context propagated in message headers).
- Example: custom span on a service method:

```kotlin
@Observed(name = "process_payment")
fun processPayment(orderId: String, amount: BigDecimal): PaymentResult {
    val span = tracer.currentSpan()
    span.setAttribute("order.id", orderId)
    span.setAttribute("payment.amount", amount.toDouble())
    // ... business logic
}
```

### Metrics

- Required metrics (exposed via `/actuator/metrics` or your metrics endpoint):
  - **HTTP**: request count, duration histogram, active requests (by method, URI, status)
  - **JVM**: heap/non-heap memory, GC pauses, thread states, class loading
  - **Connection pools**: active/idle/pending connections (HikariCP)
  - **Business metrics**: custom counters/timers/gauges for domain events
- Naming convention: `service.metric.name.unit` (dot-separated)
- Custom metrics example: timer around a business operation:

```kotlin
val orderProcessingTimer = MeterRegistry.timer("order.processing.duration",
    "service", "order-service",
    "environment", "production")

fun processOrder(order: Order) {
    orderProcessingTimer.record {
        // ... business logic
    }
}
```
- Tags/labels: always include `service`, `environment`, `instance`.

### Health Checks

- Spring Actuator `/actuator/health` with custom `HealthIndicator` implementations.
- Required indicators: database, message broker, cache, external APIs.
- Liveness vs readiness probes: `/actuator/health/liveness` and `/actuator/health/readiness` (Kubernetes-compatible).
- Each indicator with timeout — report DOWN with details on failure.
- Example: custom HealthIndicator for an external API dependency:

```kotlin
@Component
class ExternalApiHealthIndicator(
    private val externalApiClient: ExternalApiClient,
) : HealthIndicator {

    override fun health(): Health {
        return try {
            val status = externalApiClient.getStatus()
            Health.up()
                .withDetail("external-api", "reachable")
                .withDetail("latency-ms", status.latencyMs)
                .build()
        } catch (e: Exception) {
            Health.down()
                .withDetail("external-api", "unreachable")
                .withException(e)
                .build()
        }
    }
}
```

### Alerting Integration

- Reference `@.claude/rules/shared/operational-standards.md` for SLO definitions and alert thresholds.
- Structured error logging at ERROR/FATAL enables alert rules in your monitoring platform.
- Circuit breaker state changes (via Resilience4j): log and emit metrics when circuits open/close.
- JVM alerts: GC pause time > 500ms, heap usage > 85%, thread count > threshold.

## Security in Code

- `@Valid` on all controller input parameters.
- Parameterized queries (JPA handles this). No string concatenation in `@Query`.
- Hash passwords with `BCryptPasswordEncoder`.
- Secrets: never in code or `application.yml` committed to git. Use env vars or Spring Cloud Config / Vault.
- CORS: explicit origin list in `WebConfig`, never `allowedOrigins("*")` in prod.
- Method security: `@PreAuthorize("hasRole('ADMIN')")` on sensitive endpoints.
- CSRF: enabled for browser-facing APIs, disabled for pure API (JWT) services.

## Configuration

```yaml
# application.yml — defaults
spring:
  profiles:
    active: ${SPRING_PROFILES_ACTIVE:dev}
  datasource:
    url: ${DATABASE_URL}
  jpa:
    open-in-view: false          # ALWAYS false — prevent lazy-load in controller
    hibernate:
      ddl-auto: validate         # Flyway manages schema — never auto-create
  flyway:
    enabled: true

# application-prod.yml — production overrides
logging:
  level:
    root: WARN
    com.example: INFO
```

- `open-in-view: false` — always. This prevents accidental lazy loading in controllers and view rendering.
- `ddl-auto: validate` — Flyway owns the schema.
- Profile-specific configs: `dev`, `test`, `staging`, `prod`.
- All secrets via environment variables.
