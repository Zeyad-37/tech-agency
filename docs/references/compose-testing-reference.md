# Compose/Android Testing Reference

This is the detailed testing reference with code examples for Jetpack Compose/Android. See `.claude/rules/compose-coding-standards.md` for the summary rules.

## Unit Tests — JUnit 5 + Mockito + Turbine

```kotlin
@ExtendWith(MainDispatcherExtension::class)
class NotesListViewModelTest {

    @Mock
    private lateinit var getNotesUseCase: GetNotesUseCase

    @Mock
    private lateinit var deleteNoteUseCase: DeleteNoteUseCase

    @Mock
    private lateinit var analyticsService: AnalyticsService

    private lateinit var viewModel: NotesListViewModel

    @BeforeEach
    fun setUp() {
        MockitoAnnotations.openMocks(this)
    }

    @Test
    fun `when load notes succeeds then state contains notes`() = runTest {
        // Given
        val notes = listOf(Note(id = "1", title = "Test", content = "Body", createdAt = testDateTime))
        whenever(getNotesUseCase.invoke()).thenReturn(Result.success(notes))

        // When
        viewModel = NotesListViewModel(getNotesUseCase, deleteNoteUseCase, analyticsService)
        viewModel.state.test {
            // Then
            val initial = awaitItem()
            assertTrue(initial.isLoading)

            val loaded = awaitItem()
            assertFalse(loaded.isLoading)
            assertEquals(1, loaded.notes.size)
        }
    }

    @Test
    fun `when load notes fails then state has error`() = runTest {
        // Given
        whenever(getNotesUseCase.invoke()).thenReturn(Result.failure(AppError.NetworkUnavailable))

        // When
        viewModel = NotesListViewModel(getNotesUseCase, deleteNoteUseCase, analyticsService)
        viewModel.state.test {
            awaitItem() // loading
            val errorState = awaitItem()
            assertNotNull(errorState.error)
        }
    }
}
```

## InputHandler Tests — JUnit 5 + Mockito + Turbine

```kotlin
class LoadNotesInputHandlerTest {

    @Mock
    private lateinit var getNotesUseCase: GetNotesUseCase

    private lateinit var handler: LoadNotesInputHandler

    @BeforeEach
    fun setUp() {
        MockitoAnnotations.openMocks(this)
        handler = LoadNotesInputHandler(getNotesUseCase)
    }

    @Test
    fun `when load notes succeeds then emit loading and loaded`() = runTest {
        // Given
        val notes = listOf(Note.preview())
        whenever(getNotesUseCase.invoke()).thenReturn(Result.success(notes))

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

## API Tests — MockWebServer

```kotlin
class NotesApiTest {

    private lateinit var mockWebServer: MockWebServer
    private lateinit var api: NotesApi

    @BeforeEach
    fun setUp() {
        mockWebServer = MockWebServer()
        mockWebServer.start()
        api = Retrofit.Builder()
            .baseUrl(mockWebServer.url("/"))
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(NotesApi::class.java)
    }

    @AfterEach
    fun tearDown() {
        mockWebServer.shutdown()
    }

    @Test
    fun `when get notes then parse response correctly`() = runTest {
        // Given
        val json = """{"status":"success","data":[{"id":"1","title":"Test","content":"Body","created_at":"2025-01-01T12:00:00"}]}"""
        mockWebServer.enqueue(MockResponse().setBody(json).setResponseCode(200))

        // When
        val response = api.getNotes()

        // Then
        assertEquals(1, response.data.size)
        assertEquals("Test", response.data.first().title)

        val request = mockWebServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path!!.contains("api/v1/notes"))
    }

    @Test
    fun `when server returns 401 then throw HttpException`() = runTest {
        // Given
        mockWebServer.enqueue(MockResponse().setResponseCode(401))

        // When & Then
        assertThrows<HttpException> { api.getNotes() }
    }
}
```

## Compose UI Tests

```kotlin
class NotesListScreenTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun when_success_state_then_displays_notes() {
        composeRule.setContent {
            AppTheme {
                NotesListContent(
                    state = NotesListState(
                        notes = listOf(Note.preview()),
                        isLoading = false,
                    ),
                    onLoadNotes = {},
                    onDeleteNote = {},
                    onRetry = {},
                    onNoteClick = {},
                )
            }
        }

        composeRule.onNodeWithText("Test Note").assertIsDisplayed()
    }

    @Test
    fun when_loading_state_then_shows_progress() {
        composeRule.setContent {
            AppTheme {
                NotesListContent(
                    state = NotesListState(isLoading = true),
                    onLoadNotes = {},
                    onDeleteNote = {},
                    onRetry = {},
                    onNoteClick = {},
                )
            }
        }

        composeRule.onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo.Indeterminate)).assertIsDisplayed()
    }

    @Test
    fun when_error_state_then_shows_retry() {
        composeRule.setContent {
            AppTheme {
                NotesListContent(
                    state = NotesListState(
                        isLoading = false,
                        error = AppError.NetworkUnavailable,
                    ),
                    onLoadNotes = {},
                    onDeleteNote = {},
                    onRetry = {},
                    onNoteClick = {},
                )
            }
        }

        composeRule.onNodeWithText("Retry").assertIsDisplayed()
    }
}
```

## Screenshot / Visual Regression Tests (Paparazzi)

Screenshot tests catch unintended UI changes by comparing rendered output against golden reference images. Paparazzi runs on the JVM — no emulator required.

```kotlin
class NoteCardSnapshotTest {

    @get:Rule
    val paparazzi = Paparazzi(
        deviceConfig = DeviceConfig.PIXEL_6,
        theme = "Theme.App",
    )

    @Test
    fun noteCard_default_light() {
        paparazzi.snapshot {
            AppTheme(darkTheme = false) {
                NoteCard(note = Note.preview(), onClick = {}, onDelete = {})
            }
        }
    }

    @Test
    fun noteCard_default_dark() {
        paparazzi.snapshot {
            AppTheme(darkTheme = true) {
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
    fun notesListContent_allFourStates() {
        listOf(
            "loading" to NotesListState(isLoading = true),
            "error" to NotesListState(isLoading = false, error = AppError.NetworkUnavailable),
            "empty" to NotesListState(isLoading = false, notes = emptyList()),
            "success" to NotesListState(isLoading = false, notes = listOf(Note.preview())),
        ).forEach { (name, state) ->
            paparazzi.snapshot(name = "notesList_$name") {
                AppTheme {
                    NotesListContent(
                        state = state,
                        onLoadNotes = {}, onDeleteNote = {}, onRetry = {}, onNoteClick = {},
                    )
                }
            }
        }
    }
}
```

## E2E Tests (Maestro)

```yaml
# e2e/flows/create-note.yaml
appId: com.example.app
---
- launchApp
- tapOn: "Notes"
- tapOn: "Create Note"
- inputText:
    id: "titleInput"
    text: "E2E Test Note"
- inputText:
    id: "contentInput"
    text: "This is an automated test."
- tapOn: "Save"
- assertVisible: "E2E Test Note"
```

### Alternative — Compose UI Test for E2E on emulator:

```kotlin
@RunWith(AndroidJUnit4::class)
@HiltAndroidTest
class CreateNoteE2ETest {

    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun when_user_creates_note_then_appears_in_list() {
        composeRule.onNodeWithText("Create Note").performClick()
        composeRule.onNodeWithTag("titleInput").performTextInput("E2E Test Note")
        composeRule.onNodeWithTag("contentInput").performTextInput("This is an automated test.")
        composeRule.onNodeWithText("Save").performClick()

        composeRule.waitUntil(5_000) {
            composeRule.onAllNodesWithText("E2E Test Note").fetchSemanticsNodes().isNotEmpty()
        }
        composeRule.onNodeWithText("E2E Test Note").assertIsDisplayed()
    }
}
```

## Performance Benchmarking Tests (Macrobenchmark)

```kotlin
@RunWith(AndroidJUnit4::class)
class AppBenchmarks {

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
    fun startup_warm() {
        benchmarkRule.measureRepeated(
            packageName = "com.example.app",
            metrics = listOf(StartupTimingMetric()),
            iterations = 5,
            startupMode = StartupMode.WARM,
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
            repeat(3) { list.fling(Direction.DOWN) }
        }
    }
}
```

## Security Tests

```kotlin
class SecurityTest {

    @Test
    fun when_no_auth_header_then_protected_api_returns_401() = runTest {
        val mockWebServer = MockWebServer()
        mockWebServer.enqueue(MockResponse().setResponseCode(401))
        mockWebServer.start()
        // ... verify client handles 401 correctly and redirects to login
    }

    @Test
    fun when_certificate_pinning_violated_then_connection_fails() {
        val client = OkHttpClient.Builder()
            .certificatePinner(
                CertificatePinner.Builder()
                    .add("api.example.com", "sha256/INVALID_PIN")
                    .build()
            )
            .build()

        assertThrows<SSLHandshakeException> {
            client.newCall(Request.Builder().url("https://api.example.com").build()).execute()
        }
    }
}
```

## Accessibility Tests

```kotlin
class NotesListAccessibilityTest {

    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun when_note_card_then_has_content_description() {
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
    fun when_interactive_elements_then_minimum_touch_target_48dp() {
        composeRule.setContent {
            AppTheme {
                NoteCard(note = Note.preview(), onClick = {}, onDelete = {})
            }
        }

        composeRule.onAllNodes(hasClickAction())
            .assertAll(hasMinimumTouchTargetSize(48.dp, 48.dp))
    }

    @Test
    fun when_error_state_then_live_region_announced() {
        composeRule.setContent {
            AppTheme {
                NotesListContent(
                    state = NotesListState(isLoading = false, error = AppError.NetworkUnavailable),
                    onLoadNotes = {}, onDeleteNote = {}, onRetry = {}, onNoteClick = {},
                )
            }
        }

        // Error message should be in a live region for TalkBack announcement
        composeRule.onNodeWithText("No internet connection")
            .assertExists()
    }

    @Test
    fun when_200_percent_font_scale_then_no_text_clipping() {
        composeRule.setContent {
            CompositionLocalProvider(
                LocalDensity provides Density(
                    density = LocalDensity.current.density,
                    fontScale = 2.0f,
                )
            ) {
                AppTheme {
                    NoteCard(note = Note.preview(), onClick = {}, onDelete = {})
                }
            }
        }

        composeRule.onNodeWithText("Test Note").assertIsDisplayed()
    }
}
```
