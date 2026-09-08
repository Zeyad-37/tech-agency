# Compose/Android Observability Reference

This is the detailed observability reference with code examples for Jetpack Compose/Android. See `.claude/rules/mobile/android/compose-coding-standards.md` for the summary rules.

> **Shared-code constraint.** Several samples below (repositories, ViewModels) live in KMP `commonMain`, which compiles for iOS and Wasm as well as the JVM. **No `java.*` or `System.*` in those files** — `System.currentTimeMillis()` and friends resolve only on Android/JVM. Use `kotlin.time.TimeSource` for elapsed time and `kotlinx.datetime.Clock` for wall-clock timestamps. Samples that are genuinely Android-only (`Activity`, `Bundle`, `Intent`) may use platform APIs freely.

## Structured Logging

Logging in Android uses the KMP `Logger` interface. The Android implementation of `createLogger` returns a class implementing the shared `Logger` interface, delegating to the chosen logging framework (Timber, Logback, SLF4J via Logback Android, or custom).

```kotlin
// In any Android code or shared KMP code
private val logger = createLogger("NotesScreen")

fun loadNotes() {
    logger.info("Loading notes", mapOf("userId" to userId))
    try {
        val notes = repository.getNotes()
        logger.info("Notes loaded", mapOf("count" to notes.size.toString()))
    } catch (e: Exception) {
        logger.error("Failed to load notes", e, mapOf("userId" to userId))
    }
}
```

## Crash Reporting

Integrate via KMP `CrashReporter` interface. Android `actual` implementation delegates to the project's crash reporting SDK (Firebase Crashlytics, Sentry, Bugsnag, etc.).

```kotlin
class NotesViewModel : ViewModel() {
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
                val notes = repository.getNotes()
                // update state
            } catch (e: Exception) {
                crashReporter.logException(e)
            }
        }
    }
}
```

## Performance Monitoring

Use KMP `PerformanceTrace` interface. Android `actual` delegates to the project's APM tool (Firebase Performance Monitoring, New Relic, Datadog, custom).

```kotlin
class NotesRepository(private val trace: PerformanceTrace) {
    suspend fun searchNotes(query: String): List<Note> {
        val span = trace.startTrace("search.notes")
        // TimeSource.Monotonic, NOT System.currentTimeMillis(). Repositories
        // live in the KMP `data` layer's commonMain, where java.lang.System
        // does not resolve for the iOS or Wasm targets — and Monotonic is
        // immune to wall-clock adjustments besides.
        val started = TimeSource.Monotonic.markNow()
        try {
            val results = dao.search("%$query%")
            span.putMetric("duration_ms", started.elapsedNow().inWholeMilliseconds)
            span.putMetric("result_count", results.size.toLong())
            return results
        } finally {
            span.stop()
        }
    }
}
```

## App Lifecycle Observability

```kotlin
// In MainActivity or launch screen
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)

    val sessionId = UUID.randomUUID().toString()
    val crashReporter = getCrashReporter()
    crashReporter.setCustomKey("sessionId", sessionId)

    // Check intent for deep link or notification
    intent.data?.let { deepLink ->
        crashReporter.setCustomKey("attribution", "deeplink")
        crashReporter.setCustomKey("deepLinkUrl", deepLink.toString())
    }
    intent.extras?.getString("notificationId")?.let { notifId ->
        crashReporter.setCustomKey("attribution", "notification")
        crashReporter.setCustomKey("notificationId", notifId)
    }
}
```
