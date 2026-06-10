# Jetpack Compose / Android Coding Standards

Owner: Kai. All Android code MUST follow these standards. This document covers Android-specific concerns. For shared KMP architecture (MVI pattern, Clean Architecture layers, use cases, repositories, data models, Konsist enforcement), see @.claude/rules/mobile/shared/kmp-coding-standards.md — those rules apply here.

**Reading Guide**: Android development requires reading BOTH documents:
1. **KMP standards** (@.claude/rules/mobile/shared/kmp-coding-standards.md) — the foundation: architecture, MVI pattern, shared code structure, cross-platform testing
2. **This Compose standards document** — Android-specific layer: Jetpack Compose UI, Hilt DI, Retrofit networking, Android testing frameworks, Material 3 theming

## Key Differences from KMP Shared Code

| Concern | KMP (commonMain) | Android (androidApp / androidMain) |
|---------|-------------------|-------------------------------------|
| DI | Koin | Hilt |
| Testing | kotlin.test + Mokkery + Turbine | JUnit 5 + Robolectric + Mockito + Turbine |
| Networking | Ktor | Retrofit + OkHttp |
| Mocking HTTP | Ktor MockEngine | MockWebServer |
| ViewModel | KMP base `ViewModel<I, S, E>` | Same (consumed via `koinViewModel()` or wrapped with Hilt) |

## Project Structure (Platform-Native Variant — Android App Module)

This layout applies when the Android app module owns the Compose UI directly. For the Compose Multiplatform variant where UI lives in KMP `commonMain`, see `kmp-coding-standards.md` § "Compose Multiplatform UI in commonMain". The rules in the rest of this document apply to both variants unless otherwise noted.

```
androidApp/
├── src/main/kotlin/com/example/{project}/
│   ├── App.kt                        # Application class (@HiltAndroidApp)
│   ├── MainActivity.kt               # Single Activity host (@AndroidEntryPoint)
│   ├── navigation/
│   │   ├── AppNavGraph.kt            # Top-level NavHost
│   │   └── Route.kt                  # Type-safe route definitions
│   ├── features/                     # Android-specific UI per feature
│   │   └── {feature}/
│   │       ├── {Feature}Screen.kt           # Top-level screen composable
│   │       ├── components/                  # Feature-specific composables
│   │       │   └── {Component}.kt
│   │       └── di/
│   │           └── {Feature}Module.kt       # Hilt module (Android-only bindings)
│   ├── core/
│   │   ├── network/                  # Android-specific networking (Retrofit + OkHttp)
│   │   │   ├── RetrofitClient.kt     # Retrofit instance + OkHttp interceptors
│   │   │   ├── AuthInterceptor.kt    # OkHttp auth interceptor
│   │   │   └── NetworkModule.kt      # Hilt @Module providing Retrofit
│   │   ├── di/
│   │   │   └── AppModule.kt          # App-wide Hilt bindings
│   │   └── extensions/
│   ├── designsystem/                 # Reusable UI components
│   │   ├── components/
│   │   │   ├── buttons/
│   │   │   ├── cards/
│   │   │   ├── inputs/
│   │   │   └── feedback/             # Snackbars, dialogs, empty/error/loading states
│   │   ├── theme/
│   │   │   ├── Theme.kt              # Material 3 theme wrapper
│   │   │   ├── Color.kt              # Color tokens from Pixel
│   │   │   ├── Type.kt               # Typography tokens
│   │   │   └── Spacing.kt            # Spacing tokens
│   │   └── modifiers/
│   │       └── AccessibilityModifiers.kt
│   └── shared/                       # Bridge layer to consume KMP ViewModels
│       └── ViewModelBridge.kt        # Hilt providers wrapping Koin KMP ViewModels
├── src/test/                         # Unit tests (JUnit 5 + Robolectric + Mockito)
│   └── kotlin/com/example/{project}/
├── src/androidTest/                  # Instrumented + Compose UI tests
│   └── kotlin/com/example/{project}/
└── build.gradle.kts
```

**Important**: The `domain`, `data`, and `sharedPresentation` layers live in KMP feature modules (see kmp-coding-standards.md). The Android app module contains only UI (Compose screens), Android-specific DI (Hilt), and the Retrofit networking layer.

## Consuming KMP ViewModels in Compose

KMP ViewModels use the base `ViewModel<I, S, E>` with MVI. Android consumes them directly:

```kotlin
@Composable
fun NotesListScreen(
    viewModel: NotesListViewModel = koinViewModel(),
    onNavigateToDetail: (String) -> Unit = {},
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    // Collect one-shot effects
    LaunchedEffect(Unit) {
        viewModel.effect.collect { effect ->
            when (effect) {
                is NotesListEffect.NavigateToDetail -> onNavigateToDetail(effect.noteId)
                is NotesListEffect.ShowSnackbar -> snackbarHostState.showSnackbar(effect.message)
            }
        }
    }

    NotesListContent(
        state = state,
        onLoadNotes = { viewModel.process(NotesListInput.LoadNotes) },
        onDeleteNote = { id -> viewModel.process(NotesListInput.DeleteNote(id)) },
        onRetry = { viewModel.process(NotesListInput.LoadNotes) },
        onNoteClick = onNavigateToDetail,
    )
}
```

Rules:
- Use `koinViewModel()` to obtain KMP ViewModels (Koin provides them from `sharedPresentation` modules).
- Collect `state` via `collectAsStateWithLifecycle()`.
- Collect `effect` in a `LaunchedEffect(Unit)` block — effects are one-shot (navigation, snackbar).
- Send user actions via `viewModel.process(Input)` — never call ViewModel methods directly for business logic.
- If Hilt-only Android ViewModels are needed (rare), use `@HiltViewModel` + `hiltViewModel()`.

### Hilt ↔ Koin Bridge (when needed)

```kotlin
// shared/ViewModelBridge.kt — provides KMP Koin dependencies into Hilt graph
@Module
@InstallIn(SingletonComponent::class)
object KmpBridgeModule {
    @Provides
    fun provideAnalyticsService(): AnalyticsService =
        KoinPlatform.getKoin().get()
}
```

Use this pattern sparingly — only when an Android-specific component (e.g., a Hilt-injected service) needs a KMP dependency.

## Compose UI Patterns

### Screen Structure — Stateful Wrapper + Stateless Content

```kotlin
// Stateful wrapper — holds ViewModel, collects state/effects
@Composable
fun NotesListScreen(
    viewModel: NotesListViewModel = koinViewModel(),
    onNavigateToDetail: (String) -> Unit = {},
) { ... }

// Stateless content — pure, previewable, testable
@Composable
private fun NotesListContent(
    state: NotesListState,
    onLoadNotes: () -> Unit,
    onDeleteNote: (String) -> Unit,
    onRetry: () -> Unit,
    onNoteClick: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Scaffold(
        topBar = { TopAppBar(title = { Text("Notes") }) },
    ) { padding ->
        Box(modifier = modifier.padding(padding)) {
            when {
                state.isLoading -> LoadingState()
                state.error != null -> ErrorState(
                    message = state.error.toUserMessage(),
                    onRetry = onRetry,
                )
                state.notes.isEmpty() -> EmptyState(
                    message = "No notes yet",
                    icon = Icons.Outlined.StickyNote2,
                )
                else -> NotesList(
                    notes = state.notes,
                    onNoteClick = onNoteClick,
                    onDelete = onDeleteNote,
                )
            }
        }
    }
}
```

Rules:
- **Stateful wrapper + stateless content** pattern. Screen holds ViewModel; Content is pure.
- Content composable renders based on `State` fields (from the KMP contract's `data class State`).
- Navigation callbacks as lambda parameters — never pass `NavController` into composables.
- All event callbacks as lambdas with default `= {}` for previews.
- `Modifier` as the first optional parameter after required params.

### Event Callback Shape — `process: (Input) -> Unit` vs Named Lambdas

Content composables expose user events to the wrapper in one of two shapes. Pick per-screen based on what the wrapper actually does — don't mix them in a single Content.

**Default: single `process: (Input) -> Unit` callback.** Use when the wrapper is a thin dispatcher and every event maps 1:1 to a feature `Input`. Content imports the feature's `Input` sealed type and emits Inputs directly:

```kotlin
@Composable
private fun SettingsContent(
    state: SettingsState,
    process: (SettingsInput) -> Unit,
) {
    SteadyToggleRow(
        checked = state.isAppLockEnabled,
        onCheckedChange = { process(ToggleAppLockInput) },
    )
    SteadyTimePickerRow(
        time = state.notificationTime,
        onClick = { process(ShowTimePickerInput) },
    )
}
```

This is the default for any screen where events are predominantly 1:1 dispatches — settings panels, list screens, simple toggles.

**Exception: named lambdas.** Use when the wrapper genuinely *translates* between UI events and Inputs and that translation work shouldn't leak into Content. Concrete triggers:

- **State derivation** — wrapper composes a new `Input` from current `state` (e.g. `process(ValidateFormInput(state.form.copy(name = ...)))`). Pushing this into Content forces Content to import the form-state shape.
- **Permission / coroutine flows** — wrapper awaits a `PermissionsController` inside `coroutineScope.launch` before dispatching. Content must not import permission APIs or launch coroutines.
- **Local UI state mutation** — handler also touches `remember`-scoped state (T-013 cat-(e)) such as `activeSurface`, sheet state, focus requesters. The mutation isn't an Input and shouldn't be one.

A Content with a mix of pure-dispatch and translating events still takes named lambdas for *all* of them — don't pass both `process` and named lambdas to the same composable.

Form screens with field validation, screens with permission-gated actions, and screens with multiple ephemeral surfaces are typical exception cases.

### Compose Rules

- **Composable functions are PascalCase** (they represent UI elements).
- **Stateless by default**. Hoist state to the caller. Only Screen-level composables hold ViewModels.
- **No side effects in composition**. Use `LaunchedEffect`, `SideEffect`, `DisposableEffect` for effects.
- **`remember` for expensive computations** within composition. `derivedStateOf` for derived state.
- **`key` parameter on `LazyColumn`/`LazyRow` items** — always. Use stable unique IDs.
- **No nested `LazyColumn`/`LazyRow`**. Use `item {}` blocks within a single lazy list instead.
- **Preview every component** with `@Preview` in light and dark mode:

```kotlin
@Preview(showBackground = true)
@Preview(showBackground = true, uiMode = Configuration.UI_MODE_NIGHT_YES)
@Composable
private fun NoteCardPreview() {
    AppTheme {
        NoteCard(
            note = Note.preview(),
            onClick = {},
            onDelete = {},
        )
    }
}
```

## File Organization in `ui/`

These rules apply to both project-structure variants (replace `ui/` with `features/{feature}/` for the platform-native variant).

### One screen per file

Each top-level screen composable owns its file:
- `NotesListScreen.kt` exports `fun NotesListScreen(...)` (stateful wrapper) and `private fun NotesListContent(...)` (stateless content).
- Private sub-composables specific to that screen MAY stay in the same file. They MUST stay `private`.

### Pure helpers live in sibling files, never inside the screen file

Any non-Composable code — formatters, mappers, extension functions, pure constants like a `LocalDate.Format` or an ordered enum list, value classes computed from state — MUST live in a sibling file in the same package.

Naming suffixes — pick the one that matches the helper's purpose; don't invent new suffixes:

| Suffix | Use for | Example file name |
|---|---|---|
| `*Formatters.kt` | Localization-aware string builders, label resolvers | `{Screen}Formatters.kt` |
| `*UiExtensions.kt` | UI-only extensions on shared types (icons, colors, display labels) | `{SharedType}UiExtensions.kt` |
| `*Mapper.kt` | Conversions between PM/domain types and UI-display types | `{Domain}Mapper.kt` |
| `*Model.kt` | UI-only value classes/data classes derived from state | `{Component}Model.kt` |

A single helper file MAY mix categories (e.g., a `*Formatters.kt` file declares a `data class` for resolved label bundles alongside `internal fun` formatter helpers). Don't over-split.

### Composable extensions on enums

A `@Composable fun MyEnum.label(): String = stringResource(...)` lookup belongs:
- **Next to the enum source** when the enum is owned by this feature (e.g., `NoteSortOption.label()` next to `NoteSortOption.kt`).
- **In `{Type}UiExtensions.kt` in the consuming feature's `ui/`** when the enum is owned by a shared module (e.g., `NoteCategoryPM.displayLabel()` belongs in an extensions file since `NoteCategoryPM` lives in a cross-feature module like `notes/sharedPresentation`).

Never inline the lookup inside the screen file.

### Screen-local ephemeral state types

T-013 category (e) sealed types that model mutually-exclusive ephemeral UI state for one screen (e.g., "which picker is open") MAY remain in the screen file as `private sealed interface`. They are not shared by definition — don't promote them to a shared package.

## Every Screen Must Handle 4 States

The KMP `State` data class defines the state shape. Compose renders all four states:

```kotlin
// KMP contract (in sharedPresentation)
data class NotesListState(
    val notes: List<Note> = emptyList(),
    val isLoading: Boolean = true,
    val error: AppError? = null,
) : State

// Compose renders:
// 1. Loading:  state.isLoading == true
// 2. Error:    state.error != null
// 3. Empty:    state.notes.isEmpty() && !state.isLoading
// 4. Success:  state.notes.isNotEmpty()
```

No exceptions. Every screen composable covers all four.

## Render Decisions Are Typed Structures (T-013)

Every conditional in a composable falls into exactly one of five categories. The category determines the right typed structure. See `shared-standards.md` "UI Render Decisions Belong to Typed Structures" for the platform-agnostic framework; this section documents Compose-specific enforcement.

| # | Category | Right answer in Compose | Wrong answer |
|---|---|---|---|
| **a** | Data-driven shape | Sealed `*State` + exhaustive `when` at the screen root | `if (state.isLoading)`/`if (state.entries.isEmpty())` chains |
| **b** | Domain type capability | Polymorphic property on the sealed domain type (`note.canBeArchived`) | `if (note is PinnedNotePM \|\| note is ArchivedNotePM)` at the call site |
| **c** | Component variant | Sealed enum Component Prop (`titleStyle: TitleStyle.Large`) | `useLargeTitleStyle: Boolean` parameter |
| **d** | Mutually-exclusive sub-state | Single sealed field on State (`dialog: ActiveDialog?`) | N parallel `show*: Boolean` fields |
| **e** | Pure Compose-local ephemeral state | `remember { mutableStateOf(...) }` | Promoting to ViewModel State just for purity |

### Decision tree

```
Is the decision derived from data the ViewModel owns?
├── YES → Is it about overall screen shape (loading/error/etc.)?
│        ├── YES  → Category (a): sealed State + when
│        └── NO   → Is it "which of N mutually-exclusive things is active"?
│                 ├── YES → Category (d): single sealed field on State
│                 └── NO  → It's a property of a domain type → Category (b)
└── NO  → Is it about how a component looks given fixed inputs?
         ├── YES → Category (c): sealed/enum Component Prop
         └── NO  → Is it ephemeral UI state (scroll, focus, animation)?
                  └── YES → Category (e): remember-based local state
```

### Enforcement

| Rule | Tool | Scope |
|---|---|---|
| (a) `*State` types directly implementing architecture's `State` interface must be sealed | Konsist | Project-wide |
| (b) `is *PM` / `is *Domain` discriminators in feature UI code | Detekt (custom rule, e.g. `DomainTypeCheckInUiRule`) | `features/<feature>/.../ui/...` (excluding `when`-conditions, which are the right answer) |
| (c) Variant-named `Boolean` parameters on design-system Composables | Detekt (custom rule, e.g. `ComposeBooleanVariantRule`) | `<design-system-module>/components/...` |
| (d) `*State` classes with 3+ `show*: Boolean` properties | Konsist | Project-wide |

Allow-list markers (per-line):
- Rule (b): `// type-discriminator-needed: <reason>`
- Rule (c): `// component-boolean-justified: <reason>`

## Dependency Injection (Hilt — Android Only)

```kotlin
// App.kt
@HiltAndroidApp
class App : Application() {
    override fun onCreate() {
        super.onCreate()
        // Initialize Koin for KMP modules
        startKoin {
            androidContext(this@App)
            modules(allKmpModules)
        }
    }
}

// MainActivity.kt
@AndroidEntryPoint
class MainActivity : ComponentActivity() { ... }

// Android-specific Hilt modules
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideOkHttpClient(
        authInterceptor: AuthInterceptor,
    ): OkHttpClient = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) BODY else NONE
        })
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    @Provides
    @Singleton
    fun provideRetrofit(client: OkHttpClient): Retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create(
            GsonBuilder()
                .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
                .create()
        ))
        .build()
}
```

Rules:
- `@HiltAndroidApp` on Application, `@AndroidEntryPoint` on Activities.
- Koin initialized at app startup for KMP modules. Hilt for Android-only bindings.
- `@Singleton` only for truly app-wide dependencies (OkHttpClient, Retrofit, database).
- `@Provides` for third-party objects (Retrofit, OkHttp). `@Binds` for interface → implementation.
- Constructor injection everywhere. No field injection except Android framework classes.

## Networking (Retrofit + OkHttp — Android Only)

When the Android app needs its own API layer (not using KMP Ktor):

```kotlin
// Retrofit API interface
interface NotesApi {
    @GET("api/v1/notes")
    suspend fun getNotes(
        @Query("cursor") cursor: String? = null,
        @Query("limit") limit: Int = 20,
    ): ApiResponse<List<NoteDto>>

    @POST("api/v1/notes")
    suspend fun createNote(@Body request: CreateNoteRequest): ApiResponse<NoteDto>

    @DELETE("api/v1/notes/{id}")
    suspend fun deleteNote(@Path("id") id: String): ApiResponse<Unit>
}

// Repository implementation
class NotesRepositoryImpl @Inject constructor(
    private val api: NotesApi,
    private val mapper: NoteMapper,
) : NotesRepository {

    override suspend fun getNotes(): Result<List<Note>> = runCatching {
        val response = api.getNotes()
        response.data.map(mapper::toDomain)
    }.recoverCatching { throw it.toAppError() }
}
```

Rules:
- `suspend fun` on all Retrofit methods. Never callbacks.
- Return `Result<T>` from repositories.
- Map DTOs to domain models at the repository layer.
- Map Retrofit `HttpException` to `AppError` via `ErrorMapper`.
- API base URL from `BuildConfig`, not hardcoded.
- OkHttp interceptors for auth, logging, error mapping.

## Navigation (Type-Safe)

```kotlin
@Serializable
sealed class Route {
    @Serializable data object NotesList : Route()
    @Serializable data class NoteDetail(val noteId: String) : Route()
    @Serializable data object Settings : Route()
}

@Composable
fun AppNavGraph(navController: NavHostController = rememberNavController()) {
    NavHost(navController = navController, startDestination = Route.NotesList) {
        composable<Route.NotesList> {
            NotesListScreen(
                onNavigateToDetail = { noteId ->
                    navController.navigate(Route.NoteDetail(noteId))
                },
            )
        }
        composable<Route.NoteDetail> { backStackEntry ->
            val route = backStackEntry.toRoute<Route.NoteDetail>()
            NoteDetailScreen(noteId = route.noteId)
        }
    }
}
```

- Type-safe navigation with `@Serializable` routes (Navigation Compose 2.8+).
- `NavController` only in the NavGraph. Never pass it to screen composables.
- Screen composables receive navigation callbacks as lambdas.

## Testing

### Test Types & Framework Stack

| Test Type | Framework | Location | Run By |
|-----------|-----------|----------|--------|
| Unit (ViewModel, InputHandler) | JUnit 5 + Mockito + Turbine | `src/test/` | CI (every commit) |
| API (Retrofit endpoints) | JUnit 5 + MockWebServer | `src/test/` | CI (every commit) |
| Compose UI (component behavior) | Compose Test Rule | `src/androidTest/` or `src/test/` (Robolectric) | CI (every commit) |
| UI interaction tests (Input dispatch) | Compose Test Rule + capturing fake | `src/test/` (Robolectric) | CI (every commit) |
| Integration (full stack) | JUnit 5 + Hilt + Testcontainers | `src/androidTest/` | CI (every PR) |
| Screenshot / Visual Regression | Paparazzi | `src/test/` (JVM, no emulator) | CI (every PR) |
| E2E (user flows) | Maestro or Compose UI Test + Espresso | `src/androidTest/` | CI (nightly) |
| Performance Benchmarking | Jetpack Macrobenchmark | `benchmark/` module | CI (nightly) |
| Stress / Load | k6 (backend) + coroutine stress harness | `stress-tests/` | CI (pre-release) |
| Security | OWASP dependency-check + lint rules | `build-logic/` | CI (every PR) |
| Accessibility | Compose semantics assertions + TalkBack | `src/test/` + manual | CI (every PR) + manual |

> **Full reference with code examples:** See @docs/references/compose-testing-reference.md

### Testing Rules Summary

- **JUnit 5** for all Android tests (`@Test`, `@BeforeEach`, `@ExtendWith`).
- **Mockito** (`whenever`, `verify`) for mocking in Android tests. Mokkery is for KMP `commonTest` only.
- **Turbine** for testing `StateFlow` / `Flow` emissions (shared with KMP).
- **MockWebServer** for Retrofit API tests.
- **Robolectric** for tests needing Android framework without an emulator.
- **Compose test rule** for UI tests — test the stateless Content composable.
- Every stateless `*Content` composable that exposes a `process: (Input) -> Unit` lambda MUST have a Compose UI test that asserts each interactive surface in the bottom bar, action bar, or floating CTAs dispatches the correct `Input` on tap. The test runs against the stateless `Content` (no ViewModel), uses a capturing fake for `process`, and verifies the dispatched `Input` by type and payload. This is separate from screenshot tests, which verify rendering but not wiring — an accidental swap (Delete actually fires Archive) would ship under screenshot-only coverage.

```kotlin
@Test
fun delete_button_dispatches_delete_input() {
    val dispatched = mutableListOf<Input>()
    composeTestRule.setContent {
        NotesListContent(
            state = sampleSuccessState,
            snackBarHostState = remember { SnackbarHostState() },
            process = { dispatched += it },
        )
    }
    composeTestRule.onNodeWithText("Delete").performClick()
    assertTrue(dispatched.any { it is DeleteNoteInput })
}
```

- **Paparazzi** for screenshot tests — JVM only, no emulator.
- Every new screen MUST have a Paparazzi test that snapshots the entire stateless `*Content` composable end-to-end in both light and dark themes, in addition to any sub-component showcase snapshots. Component-level snapshots (showcase grids of cards, chart blocks, etc.) are valuable but do not constitute a screen-level regression baseline — the header, title block, reminder row, and action bar must all be in the frame. If Paparazzi can't resolve a `stringResource` because the Compose-resources lookup isn't available in JVM tests, thread the resolved string through `Content` as an optional parameter (e.g. `backContentDescription`, `deleteContentDescription`) — do not skip the full-screen snapshot.
- **Macrobenchmark** for performance — nightly CI on real device.
- **Given / When / Then** structure in every test.
- **Test naming**: `snake_case` matching KMP: `when_<condition>_then_<expected>` or backtick style.
- Coverage: 80%+ ViewModels/InputHandlers, 60%+ overall.
- Screenshot tests for every design system component and screen states.
- E2E tests for critical user flows (nightly).
- Security and accessibility tests run on every PR.

## Accessibility (WCAG 2.1 AA)

```kotlin
// Content descriptions on interactive elements
IconButton(onClick = { onDelete(note.id) }) {
    Icon(Icons.Default.Delete, contentDescription = "Delete ${note.title}")
}

// Semantic grouping
Row(
    modifier = Modifier.semantics(mergeDescendants = true) {
        contentDescription = "${note.title}, ${note.dateFormatted}"
    }
) {
    Text(note.title)
    Text(note.dateFormatted)
}

// Custom actions for list items
Modifier.semantics {
    customActions = listOf(
        CustomAccessibilityAction("Delete") { onDelete(note.id); true }
    )
}
```

Rules:
- **TalkBack `contentDescription`** on every interactive element and meaningful image.
- **Touch targets**: Minimum 48×48 dp. Use `Modifier.minimumInteractiveComponentSize()`.
- **Text scaling**: Use Material typography tokens (`MaterialTheme.typography`), never hardcoded `sp`. Test at 200% font scale.
- **Color contrast**: 4.5:1 normal text, 3:1 large text. Never convey meaning by color alone.
- **`mergeDescendants = true`** for logically grouped content.
- **Live region announcements**: `Modifier.semantics { liveRegion = LiveRegionMode.Polite }` for dynamic content.
- **Test with TalkBack** on a real device.

## Design System / Material 3

```kotlin
@Composable
fun AppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit,
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = AppTypography,
        content = content,
    )
}

// ALWAYS reference MaterialTheme tokens, never hardcode
Text(
    text = note.title,
    style = MaterialTheme.typography.titleMedium,
    color = MaterialTheme.colorScheme.onSurface,
)

object Spacing {
    val xxs = 4.dp
    val xs = 8.dp
    val sm = 12.dp
    val md = 16.dp
    val lg = 24.dp
    val xl = 32.dp
    val xxl = 48.dp
}
```

- Pixel's design tokens mapped to Material 3 color scheme.
- No hardcoded colors, font sizes, or spacing — always `MaterialTheme.*` or `Spacing.*`.
- Every user-facing string MUST come from a string resource — including strings produced by mapping functions (`when` over enums, formatter helpers, computed labels). A helper like `fun buildKindLabel(type): String = when (type) { MORNING -> "Routine · Morning"; ... }` is a violation even though detekt's inline-literal check won't catch it (the string isn't in a `@Composable` body). The function must either take a string-resolver and return resource-resolved values, or return a resource ID/key the caller resolves. The same applies to delta phrases (`"on track"`, `"personal best"`), cadence words (`"daily"`, `"weekly"`, `"weekdays"`), and any other dynamic UI copy.
- Dynamic color (Material You) on Android 12+, fallback to custom scheme.
- Dark mode via `isSystemInDarkTheme()` with manual toggle option.

## Performance

| Metric | Target |
|--------|--------|
| Frame render time | < 16ms (60 fps) |
| Interaction response | < 100ms |
| Cold app start | < 2s |
| Memory (idle screen) | < 80MB |

Rules:
- **`LazyColumn`/`LazyRow`** for all lists. Never `Column` with 20+ items.
- **`key` parameter** on every `items()` call with stable unique IDs.
- **`remember`** expensive computations. `derivedStateOf` for derived state.
- **Avoid allocations in composition** — no lambda creation in loops without `remember`.
- **Baseline Profiles** for optimized startup and scroll performance.
- **R8 full mode** enabled in release builds.
- Profile with **Android Studio Profiler** (Compose recomposition counts, CPU, memory).

## Security in Code

- Sensitive data: `EncryptedSharedPreferences` or Android Keystore. Never plain `SharedPreferences`.
- No sensitive data in logs. Use `BuildConfig.DEBUG` to gate verbose logging.
- Certificate pinning via OkHttp `CertificatePinner` in production.
- ProGuard/R8 rules to strip debug info from release builds.
- Network security config: HTTPS only in production, no cleartext.
- Biometric auth (`BiometricPrompt`) for sensitive operations.
- API keys in `local.properties` or BuildConfig, never committed to git.

## Observability

All observability is tool-agnostic — use your logging framework, crash reporting service, and APM tool of choice. These are integrated via KMP shared interfaces (defined in `kmp-coding-standards.md`) and Android-specific actuals in `androidMain`.

> **Full reference with code examples:** See @docs/references/compose-observability-reference.md

### Structured Logging

Logging in Android uses the KMP `Logger` interface. The Android `actual` implementation chooses the logging framework (Timber, Logback, SLF4J via Logback Android, or custom).

- Import `Logger` from KMP shared code: `expect fun createLogger(module: String): Logger`
- Android logging framework is configured at app startup in `Application.onCreate()`.
- **Log levels**: ERROR, WARN, INFO, DEBUG. Gate DEBUG logs behind `BuildConfig.DEBUG` — release builds should be INFO+ only.
- **Context fields**: Always include `traceId`, `userId`, and `module` in structured log entries where applicable.
- **Sensitive data**: NEVER log PII (email, phone), tokens, passwords. Mask or exclude entirely.

Reference `@.claude/rules/mobile/shared/kmp-coding-standards.md` for the `Logger` interface and `@.claude/rules/shared/shared-standards.md` for baseline structured logging schema.

### Crash Reporting

Integrate via KMP `CrashReporter` interface. Android `actual` implementation delegates to the project's crash reporting SDK (Firebase Crashlytics, Sentry, Bugsnag, etc.).

- Import `CrashReporter` from KMP: `expect fun getCrashReporter(): CrashReporter`
- **User binding**: Call `CrashReporter.setUserId(userId)` on login. Clear on logout with `CrashReporter.clearCustomKeys()`.
- **Breadcrumbs**: Log navigation events, network calls, and lifecycle events as breadcrumbs using `setCustomKey(key, value)`.
- **ANR detection**: Ensure the crash reporting SDK has ANR monitoring enabled in its configuration. Test with ANR Watchdog if needed.
- **ProGuard/R8 mapping**: On every release build, automatically upload the mapping file to the crash reporting service.
- **Non-fatal exceptions**: Catch unexpected exceptions indicating invalid state (e.g., null where not expected) and report via `CrashReporter.logException()`.
- **ViewModel setup**: Install a `CoroutineExceptionHandler` at ViewModel scope level to catch uncaught coroutine exceptions.

Reference `@.claude/rules/mobile/shared/kmp-coding-standards.md` for the `CrashReporter` interface.

### Performance Monitoring

Use KMP `PerformanceTrace` interface. Android `actual` delegates to the project's APM tool (Firebase Performance Monitoring, New Relic, Datadog, custom).

- Import `PerformanceTrace` from KMP: `expect fun getPerformanceTrace(): PerformanceTrace`
- **Auto-instrument**: App startup (cold + warm), screen rendering (time-to-interactive, first meaningful paint), network calls (latency, payload size, error rate), database operations, serialization/deserialization.
- **Custom traces**: Wrap critical user flows (search, checkout, media upload).
- **Screen rendering metrics**: Monitor recomposition counts via Compose metrics, track slow/frozen frames, measure jank using `FrameMetricsAggregator`.

Reference `@.claude/rules/mobile/shared/kmp-coding-standards.md` for the `PerformanceTrace` interface.

### App Lifecycle Observability

- **Session tracking**: Generate a unique session ID on app launch (e.g., UUID). Attach to all logs and crashes for grouping.
- **Foreground/background transitions**: Log app state changes — useful for understanding user behavior and app crashes.
- **First meaningful paint**: Measure time from app launch to first screen fully rendered.
- **Time-to-interactive (TTI)**: Measure when the app is responsive to user input.
- **Deep link / notification attribution**: Log the source of each app open (deep link, notification, organic).

### Alerting Thresholds

Reference `@.claude/rules/shared/operational-standards.md` for SLO definitions. Key mobile thresholds:

- **Crash-free rate**: Alert if < 99.5%
- **ANR rate**: Alert if > 0.5%
- **Cold startup P95**: Alert if > 3s
- **Warm startup P95**: Alert if > 1s
- **Network error rate**: Alert if > 2%
- **Frame drop rate**: Alert if > 5% on any screen

### Key Rules

- All observability goes through KMP shared interfaces. Android module provides the `actual` implementations (logging framework, crash SDK, APM tool, etc.).
- Inject via Hilt: ViewModels and repository classes receive `Logger`, `CrashReporter`, and `PerformanceTrace` via constructor injection. Never hardcode a vendor SDK.
- Reference `@.claude/rules/mobile/shared/kmp-coding-standards.md` for shared observability interfaces.
- Reference `@.claude/rules/shared/operational-standards.md` for SLO/alerting baselines and incident severity definitions.
- Logging library choice (Timber, Logback, SLF4J) is made at project setup. If not already chosen, Timber is recommended for its simple API and integration with Android lifecycle.
- Crash reporting SDK choice (Firebase Crashlytics, Sentry, etc.) depends on project requirements and existing infrastructure. Configure at app startup before any crashes can occur.
- APM tool choice (Firebase Performance, Datadog, New Relic) drives the `PerformanceTrace` actual implementation. Ensure auto-instrumentation is enabled for HTTP calls and database queries.

## Gradle / Build Configuration

For AGP 9.0+ upgrades or KMP+AGP incompatibilities, invoke the JetBrains `kotlin-tooling-agp9-migration` skill before changing build files (see @.claude/rules/shared/kotlin-agent-skills.md).

```kotlin
android {
    compileSdk = 35
    defaultConfig {
        minSdk = 24
        targetSdk = 35
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    kotlinOptions {
        allWarningsAsErrors = true
        freeCompilerArgs += listOf(
            "-opt-in=kotlinx.coroutines.ExperimentalCoroutinesApi",
        )
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
}
```

- **Java 21** to match KMP build requirements.
- `allWarningsAsErrors = true` — zero tolerance for warnings.
- Version catalog (`libs.versions.toml`) for all dependencies — shared with KMP modules.
- `minSdk = 24`.
- Compose BOM for aligned Compose library versions.
