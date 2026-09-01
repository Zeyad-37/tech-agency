# KMP Testing Reference

This is the detailed testing reference for KMP coding standards. See `.claude/rules/kmp-coding-standards.md` for the summary rules.

## Test Location

All shared tests in `src/commonTest/kotlin/` within each module. Platform-specific tests in `src/androidTest/`, `src/iosTest/`, etc.

## Naming Convention

`snake_case` with format: `when_<condition>_then_<expected_result>`

## Unit Tests — Use Cases

```kotlin
class GetNotesUseCaseTest {

    private val repository = mock<NotesRepository>()
    private val useCase = GetNotesUseCase(repository)

    @Test
    fun when_repository_returns_notes_then_return_success() = runTest {
        // Given
        val expected = listOf(Note(id = "1", title = "Test", content = "Content", createdAt = testDateTime))
        everySuspend { repository.getNotes() } returns Result.success(expected)

        // When
        val result = useCase()

        // Then
        assertTrue(result.isSuccess)
        assertEquals(expected, result.getOrNull())
    }

    @Test
    fun when_repository_fails_then_return_failure() = runTest {
        // Given
        everySuspend { repository.getNotes() } returns Result.failure(AppError.NetworkUnavailable)

        // When
        val result = useCase()

        // Then
        assertTrue(result.isFailure)
    }
}
```

## Unit Tests — Repositories

```kotlin
class NotesRepositoryImplTest {

    private val api = mock<NotesApi>()
    private val dao = mock<NotesDao>()
    private val mapper = NoteMapper()
    private val repository = NotesRepositoryImpl(api, dao, mapper)

    @Test
    fun when_get_notes_then_return_mapped_domain_models() = runTest {
        // Given
        val dtos = listOf(NoteDto(id = "1", title = "Test", content = "Body", createdAt = "2025-01-01T12:00:00"))
        everySuspend { api.getNotes() } returns dtos

        // When
        val result = repository.getNotes()

        // Then
        assertTrue(result.isSuccess)
        assertEquals("Test", result.getOrNull()?.first()?.title)
    }

    @Test
    fun when_observe_notes_then_return_flow_from_dao() = runTest {
        // Given
        val entities = listOf(NoteEntity(id = "1", title = "Test", content = "Body", createdAt = 1704067200000))
        every { dao.observeAll() } returns flowOf(entities)

        // When & Then
        repository.observeNotes().test {
            val notes = awaitItem()
            assertEquals(1, notes.size)
            awaitComplete()
        }
    }
}
```

## Unit Tests — InputHandlers

```kotlin
class LoadNotesInputHandlerTest {

    private val getNotesUseCase = mock<GetNotesUseCase>()
    private val handler = LoadNotesInputHandler(getNotesUseCase)

    @Test
    fun when_load_notes_succeeds_then_emit_loading_and_loaded() = runTest {
        // Given
        val notes = listOf(Note(id = "1", title = "Test", content = "Content", createdAt = testDateTime))
        everySuspend { getNotesUseCase() } returns Result.success(notes)

        // When & Then
        handler.handle(NotesListInput.LoadNotes, NotesListState()).test {
            assertIs<NotesListResult.Loading>(awaitItem())
            val loaded = awaitItem() as NotesListResult.NotesLoaded
            assertEquals(1, loaded.notes.size)
            awaitComplete()
        }
    }
}
```

## Integration Tests — Ktor MockEngine (API Layer)

```kotlin
class NotesApiIntegrationTest {

    private val mockEngine = MockEngine { request ->
        when (request.url.encodedPath) {
            "/api/v1/notes" -> respond(
                content = """{"status":"success","data":[{"id":"1","title":"Test","content":"Body","created_at":"2025-01-01T12:00:00"}]}""",
                headers = headersOf(HttpHeaders.ContentType, ContentType.Application.Json.toString()),
            )
            else -> respond("", HttpStatusCode.NotFound)
        }
    }

    private val client = HttpClient(mockEngine) {
        install(ContentNegotiation) { json(Json { ignoreUnknownKeys = true }) }
    }
    private val api = NotesApi(client)

    @Test
    fun when_get_notes_then_parse_response_correctly() = runTest {
        // When
        val notes = api.getNotes()

        // Then
        assertEquals(1, notes.size)
        assertEquals("Test", notes.first().title)
    }

    @Test
    fun when_server_returns_error_then_throw() = runTest {
        val errorEngine = MockEngine { respond("", HttpStatusCode.InternalServerError) }
        val errorClient = HttpClient(errorEngine)
        val errorApi = NotesApi(errorClient)

        // When & Then
        assertFailsWith<Exception> { errorApi.getNotes() }
    }
}
```

## Integration Tests — Database (Testcontainers, JVM only)

```kotlin
// src/jvmTest/ — runs against real database
class NotesRepositoryDbTest {

    companion object {
        private val postgres = PostgreSQLContainer("postgres:16-alpine")

        @BeforeAll
        @JvmStatic
        fun startDb() {
            postgres.start()
            Database.connect(postgres.jdbcUrl, user = postgres.username, password = postgres.password)
            transaction { SchemaUtils.create(NoteTable) }
        }

        @AfterAll
        @JvmStatic
        fun stopDb() { postgres.stop() }
    }

    private val repository = NotesRepository()

    @Test
    fun when_create_and_retrieve_note_then_data_persists() = runTest {
        // Given
        val request = CreateNoteRequest(title = "Integration Test", content = "Body")

        // When
        val created = repository.create(request, testUserId)
        val retrieved = repository.getById(created.id)

        // Then
        assertNotNull(retrieved)
        assertEquals("Integration Test", retrieved.title)
    }
}
```

## Screenshot / Visual Regression Tests

Screenshot tests catch unintended UI changes by comparing rendered output against golden reference images.

### Android (Paparazzi — runs on JVM, no emulator needed)

```kotlin
// androidApp/src/test/kotlin/.../NoteCardSnapshotTest.kt
class NoteCardSnapshotTest {

    @get:Rule
    val paparazzi = Paparazzi(
        deviceConfig = DeviceConfig.PIXEL_6,
        theme = "Theme.App",
    )

    @Test
    fun noteCard_default() {
        paparazzi.snapshot {
            AppTheme {
                NoteCard(note = Note.preview(), onClick = {}, onDelete = {})
            }
        }
    }

    @Test
    fun noteCard_longTitle() {
        paparazzi.snapshot {
            AppTheme {
                NoteCard(
                    note = Note.preview().copy(title = "A".repeat(200)),
                    onClick = {},
                    onDelete = {},
                )
            }
        }
    }

    @Test
    fun notesListContent_emptyState() {
        paparazzi.snapshot {
            AppTheme {
                NotesListContent(
                    state = NotesListState(isLoading = false, notes = emptyList()),
                    onLoadNotes = {}, onDeleteNote = {}, onRetry = {}, onNoteClick = {},
                )
            }
        }
    }
}
```

### iOS (swift-snapshot-testing)

```swift
// iosApp/Tests/NoteCardSnapshotTests.swift
import SnapshotTesting
import SwiftUI

final class NoteCardSnapshotTests: XCTestCase {
    func test_noteCard_default() {
        let view = NoteCardView(note: .preview)
        assertSnapshot(of: view, as: .image(layout: .fixed(width: 375, height: 120)))
    }

    func test_noteCard_darkMode() {
        let view = NoteCardView(note: .preview).environment(\.colorScheme, .dark)
        assertSnapshot(of: view, as: .image(layout: .fixed(width: 375, height: 120)))
    }
}
```

Rules:
- Golden images committed to git. CI fails if screenshots differ beyond a 0.1% pixel tolerance.
- Test every design system component (all variants, light/dark, RTL).
- Test each screen in all 4 states (loading, error, empty, success).
- Update golden images intentionally via `record = true` (Paparazzi) or `isRecording = true` (swift-snapshot-testing), then commit.
- Convention plugin `playground.screenshot.gradle.kts` configures Paparazzi for all UI modules.

## Performance Benchmarking Tests

Performance benchmarks prevent regressions in critical code paths.

### KMP Shared Code — kotlinx-benchmark

```kotlin
// benchmark/src/commonMain/kotlin/.../NoteMapperBenchmark.kt
@State(Scope.Benchmark)
@Warmup(iterations = 5)
@Measurement(iterations = 10)
class NoteMapperBenchmark {

    private val mapper = NoteMapper()
    private val dtos = (1..1000).map {
        NoteDto(id = "$it", title = "Note $it", content = "Content", createdAt = "2025-01-01T12:00:00")
    }

    @Benchmark
    fun mapDtosToModel(): List<Note> = dtos.map(mapper::toDomain)
}
```

### Android — Jetpack Macrobenchmark (startup, scroll, frame timing)

```kotlin
// benchmark/src/androidTest/kotlin/.../StartupBenchmark.kt
@RunWith(AndroidJUnit4::class)
class StartupBenchmark {

    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun startup_cold() {
        benchmarkRule.measureRepeated(
            packageName = "com.example.app",
            metrics = listOf(StartupTimingMetric()),
            iterations = 5,
            startupMode = StartupMode.COLD,
        ) {
            pressHome()
            startActivityAndWait()
        }
    }

    @Test
    fun scroll_notesList() {
        benchmarkRule.measureRepeated(
            packageName = "com.example.app",
            metrics = listOf(FrameTimingMetric()),
            iterations = 5,
        ) {
            startActivityAndWait()
            val list = device.findObject(By.res("notesList"))
            list.setGestureMargin(device.displayWidth / 5)
            list.fling(Direction.DOWN)
        }
    }
}
```

Rules:
- Benchmarks run nightly in CI, not on every commit (they're slow).
- Results tracked over time. Alert if P50 regresses >10% or P99 regresses >20%.
- KMP shared code: benchmark serialization, mapping, and use case execution.
- Android: cold/warm startup, scroll performance (frame timing), and screen transition time.
- iOS: use XCTest metrics (`measure(metrics: [XCTClockMetric()])`) for equivalent benchmarks.
- Performance budgets defined in `docs/guides/performance-budgets.md`.

## Stress / Load Tests

Stress tests validate the system under high concurrency and sustained load.

### KMP Coroutine Stress Tests (shared logic under contention)

```kotlin
class ViewModelStressTest {

    @Test
    fun when_rapid_inputs_then_state_remains_consistent() = runTest {
        val viewModel = NotesListViewModel(FakeGetNotesUseCase(), FakeDeleteNoteUseCase(), FakeAnalyticsService())

        // Fire 100 inputs concurrently
        val jobs = (1..100).map { i ->
            launch {
                viewModel.process(NotesListInput.LoadNotes)
                if (i % 3 == 0) viewModel.process(NotesListInput.DeleteNote("note-$i"))
            }
        }
        jobs.joinAll()

        // State should be valid (not corrupted)
        val finalState = viewModel.state.value
        assertNotNull(finalState)
        assertFalse(finalState.isLoading) // should have settled
    }
}
```

### Backend Load Tests (k6 — runs against staging server)

```javascript
// stress-tests/k6/notes-load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    stages: [
        { duration: '30s', target: 50 },   // ramp up
        { duration: '2m', target: 50 },     // sustain
        { duration: '30s', target: 200 },   // spike
        { duration: '1m', target: 200 },    // sustain spike
        { duration: '30s', target: 0 },     // ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<500', 'p(99)<1000'],
        http_req_failed: ['rate<0.01'],
    },
};

export default function () {
    const res = http.get(`${__ENV.BASE_URL}/api/v1/notes?limit=20`);
    check(res, {
        'status is 200': (r) => r.status === 200,
        'response time < 500ms': (r) => r.timings.duration < 500,
    });
    sleep(1);
}
```

Rules:
- Coroutine stress tests validate shared ViewModel/InputHandler thread safety under concurrent access.
- k6 load tests run against staging before every release.
- Thresholds: P95 < 500ms, P99 < 1000ms, error rate < 1%.
- Include spike tests (sudden traffic surge) and soak tests (sustained load over 30+ minutes).
- Results stored in `docs/load-test-results/` with date-stamped reports.

## Security Tests

Security tests validate authentication, authorization, input sanitization, and dependency safety.

### Dependency Vulnerability Scanning

```kotlin
// build-logic/plugins/playground.security.gradle.kts
plugins {
    id("org.owasp.dependencycheck")
}

dependencyCheck {
    failBuildOnCVSS = 7.0f  // fail on HIGH and CRITICAL
    suppressionFile = "config/owasp-suppressions.xml"
    analyzers.apply {
        assemblyEnabled = false
        nodeEnabled = false
    }
}
```

### Detekt Custom Security Rules

```kotlin
// build-logic/detekt-rules/
// Custom rules to catch:
// 1. Hardcoded secrets (API keys, passwords in string literals)
// 2. Use of !! in production code (crash risk)
// 3. PII logged without masking
// 4. Unencrypted storage of sensitive data (SharedPreferences without encryption)
```

### Auth & Authorization Tests

```kotlin
class AuthSecurityTest {

    @Test
    fun when_no_token_then_protected_endpoint_returns_401() = testApplication {
        application { module() }

        val response = client.delete("/api/v1/notes/1")
        assertEquals(HttpStatusCode.Unauthorized, response.status)
    }

    @Test
    fun when_expired_token_then_returns_401() = testApplication {
        application { module() }

        val expiredToken = JwtConfig.generateToken(testUserId, expiresIn = -1.hours)
        val response = client.delete("/api/v1/notes/1") {
            bearerAuth(expiredToken)
        }
        assertEquals(HttpStatusCode.Unauthorized, response.status)
    }

    @Test
    fun when_user_deletes_other_users_note_then_returns_403() = testApplication {
        application { module() }

        val token = JwtConfig.generateToken(otherUserId)
        val response = client.delete("/api/v1/notes/${testUserNoteId}") {
            bearerAuth(token)
        }
        assertEquals(HttpStatusCode.Forbidden, response.status)
    }

    @Test
    fun when_sql_injection_in_query_param_then_handled_safely() = testApplication {
        application { module() }

        val response = client.get("/api/v1/notes?cursor='; DROP TABLE notes; --")
        // Should return 400 (bad cursor format), NOT execute injection
        assertNotEquals(HttpStatusCode.InternalServerError, response.status)
    }
}
```

Rules:
- OWASP dependency check runs on every PR. Fail build on CVSS >= 7.0.
- Detekt custom rules enforce no hardcoded secrets, no `!!`, no PII in logs.
- Auth tests cover: missing token, expired token, wrong user, tampered token.
- Input sanitization tests for SQL injection, XSS payloads, path traversal.
- Security tests are part of CI — they run on every PR alongside unit tests.
- @Shield reviews security test coverage for each feature as part of the security review process.

## Accessibility Tests

Accessibility tests verify that the UI is usable by screen readers (TalkBack, VoiceOver) and meets WCAG 2.1 AA.

### Android Compose — Semantic Assertions

```kotlin
class NotesListAccessibilityTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun when_note_card_displayed_then_has_content_description() {
        composeRule.setContent {
            AppTheme {
                NoteCard(note = Note.preview(), onClick = {}, onDelete = {})
            }
        }

        composeRule.onNodeWithContentDescription("Delete Test Note")
            .assertExists()
            .assertHasClickAction()
    }

    @Test
    fun when_loading_state_then_progress_is_announced() {
        composeRule.setContent {
            AppTheme {
                NotesListContent(
                    state = NotesListState(isLoading = true),
                    onLoadNotes = {}, onDeleteNote = {}, onRetry = {}, onNoteClick = {},
                )
            }
        }

        composeRule.onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo.Indeterminate))
            .assertExists()
    }

    @Test
    fun when_interactive_elements_then_minimum_touch_target() {
        composeRule.setContent {
            AppTheme {
                NoteCard(note = Note.preview(), onClick = {}, onDelete = {})
            }
        }

        composeRule.onAllNodes(hasClickAction())
            .assertAll(hasMinimumTouchTargetSize(48.dp, 48.dp))
    }

    @Test
    fun when_error_state_then_retry_button_has_role() {
        composeRule.setContent {
            AppTheme {
                NotesListContent(
                    state = NotesListState(isLoading = false, error = AppError.NetworkUnavailable),
                    onLoadNotes = {}, onDeleteNote = {}, onRetry = {}, onNoteClick = {},
                )
            }
        }

        composeRule.onNodeWithText("Retry")
            .assertHasClickAction()
            .assertIsEnabled()
    }
}
```

### iOS — VoiceOver Assertions

```swift
func test_noteCard_hasAccessibilityLabel() {
    let view = NoteCardView(note: .preview)
    let host = UIHostingController(rootView: view)
    host.loadViewIfNeeded()

    let element = host.view.accessibilityElements?.first
    XCTAssertNotNil(element?.accessibilityLabel)
    XCTAssertTrue(element?.accessibilityTraits.contains(.button) ?? false)
}
```

Rules:
- Every interactive Compose element must have `contentDescription` — test for it.
- Touch targets >= 48dp — assert with `hasMinimumTouchTargetSize()`.
- Every screen tested for all 4 states (loading, error, empty, success) with correct semantic announcements.
- Font scaling tested at 200% on both platforms.
- CI runs accessibility checks on every PR. Manual TalkBack/VoiceOver walkthroughs required before release.
- Accessibility regressions are P1 bugs (see operational-standards.md).

## Cross-Platform Testing Coordination

When shared KMP code in `commonMain` is modified, all consuming platforms must verify compatibility before merge. This prevents a change that works on one platform from breaking another.

Rules:

- Any PR that modifies `commonMain` code MUST be reviewed and tested by all platform consumers:
  - @Swift (iOS) — run iOS tests, verify KMP framework builds, check expect/actual compatibility.
  - @Kai (Android) — run Android tests, verify Gradle sync, check Hilt/Koin bridge.
  - @Nova (Web, if applicable) — run web target tests, verify Wasm/JS build.
  - @Link (Ktor server, if applicable) — run server tests, verify shared DTO/validation compatibility.

- Sign-off requirement: The PR must have explicit approval from at least the iOS and Android consumers (the primary KMP targets). Web and server consumers sign off if they depend on the changed module.

- CI enforcement: The PR checks workflow must build and test all targets. A `commonMain` change that passes Android tests but fails iOS tests is not mergeable.

- Expect/actual changes: Any modification to an `expect` declaration requires corresponding `actual` updates across all platform source sets. The PR author is responsible for updating all actuals, or coordinating with the platform agent who owns the actual.

- Breaking changes in shared modules: If a change to `commonMain` requires consuming platform code to change (e.g., new required parameter, renamed class, changed return type):
  1. The PR author notifies all consumers via @Atlas.
  2. Platform agents update their code on the same branch or coordinated branches.
  3. All platform builds must pass before merge.

- Shared DTO/validation changes: If shared DTOs or validation rules are modified, both the Ktor server (if applicable) and all client platforms must verify. Compile-time safety covers type changes, but behavioral changes in validation logic require explicit test verification on both server and client.

Coordination flow:

```
Link modifies commonMain
  ├── Opens PR, tags @Swift @Kai @Nova (if web target exists)
  ├── CI builds all targets (Android, iOS, Web, Server)
  ├── @Swift runs iOS-specific integration tests
  ├── @Kai runs Android-specific integration tests
  ├── Both approve (or request changes)
  └── Merge only after all platform approvals + CI green
```
