# KMP Observability Reference

This is the detailed observability reference for KMP coding standards. See `.claude/rules/mobile/shared/kmp-coding-standards.md` for the summary rules.

> **Shared-code constraint for every sample below.** All of this lives in `commonMain`, so it must compile for iOS and Wasm as well as the JVM. No `java.*` imports, and no `System.*` — `System.currentTimeMillis()`, `System.nanoTime()` and `System.getenv()` are JVM-only and break the Apple and web targets. Use `kotlin.time.TimeSource` for elapsed time and `kotlinx.datetime.Clock` for wall-clock timestamps.

## Structured Logging

Define a `Logger` **interface** in `commonMain`. It is a plain interface, not an `expect interface`: an `expect interface` demands an `actual interface` on every target, which platform classes would then have to implement *in addition to* the common one — the delegating-class pattern below would not compile. Only the factory needs an `expect`/`actual` seam.

```kotlin
// shared/src/commonMain/kotlin/com/example/shared/observability/Logger.kt
interface Logger {
    fun error(message: String, throwable: Throwable? = null, context: Map<String, String> = emptyMap())
    fun warn(message: String, context: Map<String, String> = emptyMap())
    fun info(message: String, context: Map<String, String> = emptyMap())
    fun debug(message: String, context: Map<String, String> = emptyMap())
}

// The ONLY expect/actual seam — a function, whose signature is identical
// on every target.
expect fun createLogger(module: String): Logger
```

Each platform's `actual createLogger` returns a class implementing the common `Logger` by delegating to your logging framework:

- Android actual: Use the project's chosen logging framework (Timber, Logback, or custom).
- iOS actual: Use `os_log` or the project's chosen framework.
- JVM/server actual: Use SLF4J-compatible framework (Logback, Log4j2).

Rules:

- Always include contextual fields in structured logs: `traceId`, `userId`, `module` where applicable.
- Log levels: `ERROR` (unexpected failures), `WARN` (expected issues), `INFO` (state changes), `DEBUG` (verbose, typically off in production).
- NEVER log PII, tokens, passwords. Mask sensitive fields in log contexts.
- Reference `@.claude/rules/shared/shared-standards.md` for baseline logging structure (`level`, `timestamp`, `service`, `traceId`, `userId`).

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
interface CrashReporter {
    fun logException(throwable: Throwable, context: Map<String, String> = emptyMap())
    fun setUserId(userId: String)
    fun setCustomKey(key: String, value: String)
    fun clearCustomKeys()

    /**
     * Records a navigational or lifecycle breadcrumb. Breadcrumbs are the
     * trail attached to the next crash report — they are what turns "NPE in
     * NotesRepository" into "NPE in NotesRepository, two screens after a
     * failed refresh".
     *
     * Never put PII, tokens, or request bodies in [message].
     */
    fun addBreadcrumb(message: String, level: BreadcrumbLevel = BreadcrumbLevel.INFO)
}

enum class BreadcrumbLevel { DEBUG, INFO, WARNING, ERROR }

// Plain interface + one expect factory, same as Logger above.
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

// Plain interface — consistent with Logger and CrashReporter above.
interface PerformanceTrace {
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
        // TimeSource.Monotonic, NOT System.currentTimeMillis(): this class is
        // in commonMain, so a java.lang.System call would fail to compile for
        // iOS and Wasm. Monotonic is also immune to wall-clock adjustments,
        // which can otherwise produce negative durations.
        val started = TimeSource.Monotonic.markNow()
        try {
            val response = client.get("api/v1/notes").body<ApiResponse<List<NoteDto>>>()
            span.putMetric("duration_ms", started.elapsedNow().inWholeMilliseconds)
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

Ktor's **client** logging plugin is `Logging`. `CallLogging` is the *server* plugin and has no client counterpart — `HttpCallLogging` does not exist at all. Per-request/response hooks come from a custom plugin built with `createClientPlugin`, not from config lambdas on `Logging`.

```kotlin
// shared/src/commonMain/kotlin/com/example/shared/network/ObservabilityPlugin.kt
import io.ktor.client.HttpClientConfig
import io.ktor.client.plugins.HttpRequestRetry
import io.ktor.client.plugins.api.Send
import io.ktor.client.plugins.api.createClientPlugin
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.http.HttpHeaders
import kotlin.time.TimeSource

/** Trace-header propagation, latency metrics, and structured request logging. */
fun observabilityPlugin(logger: Logger, trace: PerformanceTrace) =
    createClientPlugin("Observability") {
        onRequest { request, _ ->
            request.headers.append("X-Trace-Id", newTraceId())
        }

        // `Send` wraps the whole call, so it can time it and see the response.
        on(Send) { request ->
            val span = trace.startTrace("http.${request.method.value}.${request.url.encodedPath}")
            val started = TimeSource.Monotonic.markNow()
            try {
                val call = proceed(request)
                span.putMetric("duration_ms", started.elapsedNow().inWholeMilliseconds)
                logger.info(
                    "http_response",
                    mapOf(
                        "method" to request.method.value,
                        // encodedPath only — the query string routinely carries
                        // ids, emails, and search terms.
                        "path" to request.url.encodedPath,
                        "status" to call.response.status.value.toString(),
                    ),
                )
                call
            } finally {
                span.stop()
            }
        }
    }

fun HttpClientConfig<*>.installObservability(logger: Logger, trace: PerformanceTrace) {
    install(observabilityPlugin(logger, trace))

    install(Logging) {
        // HEADERS or lower in production. LogLevel.BODY prints request and
        // response bodies in full, PII included.
        level = LogLevel.HEADERS
        filter { request -> !request.url.encodedPath.endsWith("/health") }
        sanitizeHeader { header ->
            header == HttpHeaders.Authorization || header == "X-API-Key"
        }
    }

    install(HttpRequestRetry) {
        retryOnServerErrors(maxRetries = 3)
        // The parameter is `millis`, not `delayMillis`.
        constantDelay(millis = 100)
    }
}
```

Note this is an extension on `HttpClientConfig<*>`, called from inside the `HttpClient { }` builder. Plugins cannot be installed on an already-constructed `HttpClient`.

Rules:

- Every Ktor `HttpClient` configured in commonMain must install observability plugins.
- Trace header key typically `X-Trace-Id` (align with your backend convention).
- Request/response logging: sanitize `Authorization`, `X-API-Key`, and PII from request/response bodies.
- Metrics collection: request count (counter), latency (histogram), error rate (counter) — aggregate at your metrics backend.
- Reference `@.claude/rules/shared/operational-standards.md` for SLO targets and alerting thresholds.

## Key Rules

- All observability contracts are **plain interfaces** in `commonMain`; only the factories (`createLogger`, `getCrashReporter`, `getPerformanceTrace`) use `expect`/`actual`. No hardcoded vendor dependencies in shared code.
- No `java.*` or `System.*` in any of it — these files compile for iOS and Wasm too. Elapsed time comes from `kotlin.time.TimeSource`, wall-clock time from `kotlinx.datetime.Clock`.
- Platform implementations are injected via Koin (for Android/iOS) or your DI system (for JVM) — never hardcoded.
- ViewModel scope: always install `CoroutineExceptionHandler` to catch exceptions.
- Reference `@.claude/rules/shared/shared-standards.md` for the baseline structured logging contract (fields: `level`, `timestamp`, `service`, `traceId`, `userId`).
- Reference `@.claude/rules/shared/operational-standards.md` for SLO definitions and alerting baselines per service.
