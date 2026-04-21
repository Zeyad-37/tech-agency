# KMP Observability Reference

This is the detailed observability reference for KMP coding standards. See `.claude/rules/kmp-coding-standards.md` for the summary rules.

## Structured Logging

Define a `Logger` interface in `commonMain`:

```kotlin
// shared/src/commonMain/kotlin/com/example/shared/observability/Logger.kt
expect interface Logger {
    fun error(message: String, throwable: Throwable? = null, context: Map<String, String> = emptyMap())
    fun warn(message: String, context: Map<String, String> = emptyMap())
    fun info(message: String, context: Map<String, String> = emptyMap())
    fun debug(message: String, context: Map<String, String> = emptyMap())
}

expect fun createLogger(module: String): Logger
```

Platform actuals (`androidMain`, `iosMain`, `jvmMain`) implement `Logger` by delegating to your logging framework:

- Android actual: Use the project's chosen logging framework (Timber, Logback, or custom).
- iOS actual: Use `os_log` or the project's chosen framework.
- JVM/server actual: Use SLF4J-compatible framework (Logback, Log4j2).

Rules:

- Always include contextual fields in structured logs: `traceId`, `userId`, `module` where applicable.
- Log levels: `ERROR` (unexpected failures), `WARN` (expected issues), `INFO` (state changes), `DEBUG` (verbose, typically off in production).
- NEVER log PII, tokens, passwords. Mask sensitive fields in log contexts.
- Reference `@.claude/rules/shared-standards.md` for baseline logging structure (`level`, `timestamp`, `service`, `traceId`, `userId`).

Example usage:

```kotlin
// In any shared KMP code
private val logger = createLogger("NotesRepository")

suspend fun getNotes(): List<Note> {
    logger.info("Fetching notes", mapOf("userId" to currentUserId))
    try {
        val notes = apiClient.getNotes()
        logger.info("Notes fetched", mapOf("count" to notes.size.toString()))
        return notes
    } catch (e: Exception) {
        logger.error("Failed to fetch notes", e, mapOf("userId" to currentUserId))
        throw e
    }
}
```

## Crash Reporting

Define a `CrashReporter` interface in `commonMain`:

```kotlin
// shared/src/commonMain/kotlin/com/example/shared/observability/CrashReporter.kt
expect interface CrashReporter {
    fun logException(throwable: Throwable, context: Map<String, String> = emptyMap())
    fun setUserId(userId: String)
    fun setCustomKey(key: String, value: String)
    fun clearCustomKeys()
}

expect fun getCrashReporter(): CrashReporter
```

Platform actuals (`androidMain`, `iosMain`, `jvmMain`) implement `CrashReporter` by delegating to:

- Android actual: Firebase Crashlytics, Sentry, Bugsnag, or other crash reporting SDK.
- iOS actual: Firebase Crashlytics, Sentry, or platform SDK.
- JVM/server actual: Sentry, Honeycomb, or custom error tracking.

Rules:

- All uncaught exceptions in coroutines MUST be caught and reported via `CrashReporter.logException()`.
- Install a `CoroutineExceptionHandler` at the ViewModel scope level to catch exceptions that would otherwise crash the app.
- Call `CrashReporter.setUserId()` on login and `CrashReporter.clearCustomKeys()` on logout.
- Include relevant context (screen name, operation, user action) via `setCustomKey()` as breadcrumbs.

Example usage in ViewModels:

```kotlin
// In KMP common ViewModel or platform ViewModel
class NotesViewModel(private val notesUseCase: GetNotesUseCase) : ViewModel() {
    private val crashReporter = getCrashReporter()

    private val exceptionHandler = CoroutineExceptionHandler { _, exception ->
        crashReporter.logException(exception, mapOf(
            "screen" to "NotesScreen",
            "operation" to "loadNotes"
        ))
    }

    private val scope = viewModelScope + exceptionHandler

    fun loadNotes() {
        scope.launch {
            try {
                val notes = notesUseCase()
                // ... update state ...
            } catch (e: Exception) {
                crashReporter.logException(e)
                // handle error
            }
        }
    }
}
```

## Performance Monitoring

Define a `PerformanceTrace` interface in `commonMain`:

```kotlin
// shared/src/commonMain/kotlin/com/example/shared/observability/PerformanceTrace.kt
interface Trace {
    fun stop()
    fun putMetric(key: String, value: Long)
}

expect interface PerformanceTrace {
    fun startTrace(name: String): Trace
}

expect fun getPerformanceTrace(): PerformanceTrace
```

Platform actuals delegate to:

- Android actual: Firebase Performance Monitoring or custom APM.
- iOS actual: Firebase Performance Monitoring or custom APM.
- JVM/server actual: OpenTelemetry (see Observability section in operational-standards.md).

Rules:

- Instrument critical paths: network calls (Ktor client), database operations (Exposed/Room), serialization/deserialization.
- Trace names should be descriptive: `apiCall.getUsers`, `db.query.notesSelectAll`, `serialization.json.decodeNote`.
- Use `putMetric()` to record custom measurements (latency, payload size, item count).

Example usage:

```kotlin
// Instrument network calls
class NotesApi(private val client: HttpClient) {
    private val trace = getPerformanceTrace()

    suspend fun getNotes(): List<NoteDto> {
        val span = trace.startTrace("apiCall.getNotes")
        try {
            val startTime = System.currentTimeMillis()
            val response = client.get("api/v1/notes").body<ApiResponse<List<NoteDto>>>()
            val duration = System.currentTimeMillis() - startTime
            span.putMetric("duration_ms", duration)
            span.putMetric("item_count", response.data.size.toLong())
            return response.data
        } finally {
            span.stop()
        }
    }
}
```

## Network Observability (Ktor Client)

For KMP projects using a Ktor `HttpClient`, create a plugin that:

1. Adds tracing headers to all requests (trace ID propagation).
2. Logs requests/responses with sanitized bodies (exclude auth headers and PII).
3. Collects metrics (request count, latency, error rate) and feeds them to your metrics backend.

```kotlin
// shared/src/commonMain/kotlin/com/example/shared/network/ObservabilityPlugin.kt
fun HttpClient.installObservabilityPlugin(
    logger: Logger,
    trace: PerformanceTrace,
) {
    install(HttpCallLogging) {
        level = LogLevel.INFO
        filter { request ->
            request.url.pathSegments.any { it != "health" }
        }
        sanitizeHeader { name ->
            name == HttpHeaders.Authorization || name == "X-API-Key"
        }
        requestFilter { request ->
            logger.info("Request: ${request.method.value} ${request.url.pathSegments.joinToString("/")}")
        }
        responseFilter { response ->
            logger.info("Response: ${response.status}", mapOf(
                "statusCode" to response.status.value.toString(),
                "url" to response.request.url.encodedPath,
            ))
        }
    }

    install(HttpRequestRetry) {
        // Retry logic + metrics collection
        retryOnServerErrors(maxRetries = 3)
        constantDelay(delayMillis = 100)
    }
}
```

Rules:

- Every Ktor `HttpClient` configured in commonMain must install observability plugins.
- Trace header key typically `X-Trace-Id` (align with your backend convention).
- Request/response logging: sanitize `Authorization`, `X-API-Key`, and PII from request/response bodies.
- Metrics collection: request count (counter), latency (histogram), error rate (counter) — aggregate at your metrics backend.
- Reference `@.claude/rules/operational-standards.md` for SLO targets and alerting thresholds.

## Key Rules

- All observability interfaces live in `commonMain` with `expect`/`actual` — no hardcoded vendor dependencies in shared code.
- Platform implementations are injected via Koin (for Android/iOS) or your DI system (for JVM) — never hardcoded.
- ViewModel scope: always install `CoroutineExceptionHandler` to catch exceptions.
- Reference `@.claude/rules/shared-standards.md` for the baseline structured logging contract (fields: `level`, `timestamp`, `service`, `traceId`, `userId`).
- Reference `@.claude/rules/operational-standards.md` for SLO definitions and alerting baselines per service.
