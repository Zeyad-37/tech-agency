# Compose/Android Observability Reference

This is the detailed observability reference with code examples for Jetpack Compose/Android. See `.claude/rules/compose-coding-standards.md` for the summary rules.

## Structured Logging

Logging in Android uses the KMP `Logger` interface. The Android `actual` implementation chooses the logging framework (Timber, Logback, SLF4J via Logback Android, or custom).

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
        try {
            val startTime = System.currentTimeMillis()
            val results = dao.search("%$query%")
            val duration = System.currentTimeMillis() - startTime
            span.putMetric("duration_ms", duration)
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
