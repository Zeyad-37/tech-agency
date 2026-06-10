# Kotlin Multiplatform (KMP) Coding Standards

Owners: Link (shared modules + Ktor server + web targets), Kai (Android integration), Swift (iOS integration), Nova (web integration). All KMP shared code MUST follow these standards.

## Project Structure

```
project/
├── build-logic/
│   └── plugins/                        # Convention plugins
│       ├── playground.multiplatform.lib.gradle.kts
│       ├── playground.testing.gradle.kts
│       ├── playground.koin.gradle.kts
│       ├── playground.room.gradle.kts
│       ├── playground.compose.multiplatform.gradle.kts
│       ├── playground.detekt.gradle.kts
│       └── playground.koverage.gradle.kts
├── core/                               # Shared foundational modules
│   ├── architecture/                   # Base ViewModel, MVI contracts, analytics
│   │   └── src/commonMain/kotlin/
│   │       └── presentation/
│   │           ├── Contract.kt         # Input, Result, Effect, State, InputHandler
│   │           ├── ViewModel.kt        # Base MVI ViewModel
│   │           └── AnalyticsService.kt # Track interface + service
│   ├── database/                       # Room/SQLDelight setup
│   ├── network/                        # Ktor client config
│   ├── test-base/                      # Test utilities (FakeTimeService, etc.)
│   └── utils/                          # Shared utilities
├── features/                           # Feature modules
│   └── {feature}/
│       ├── domain/                     # Business logic (platform-independent)
│       │   └── src/commonMain/kotlin/
│       │       ├── model/              # Domain entities
│       │       ├── usecase/            # Single-responsibility use cases
│       │       └── repository/         # Repository interfaces
│       ├── data/                       # Data layer implementation
│       │   └── src/commonMain/kotlin/
│       │       ├── repository/         # Repository implementations
│       │       ├── remote/             # API services + DTOs
│       │       ├── local/              # DAOs + entities
│       │       ├── mapper/             # DTO ↔ domain mappers
│       │       └── di/                 # Koin module
│       └── sharedPresentation/         # Shared presentation (ViewModels)
│           └── src/commonMain/kotlin/
│               └── {screen}/
│                   ├── viewmodel/
│                   │   ├── {Screen}ViewModel.kt
│                   │   ├── {Screen}Contract.kt    # Input, State, Effect
│                   │   └── inputhandler/
│                   │       └── {Action}InputHandler.kt
│                   └── di/
│                       └── {Screen}Module.kt
├── androidApp/                         # Android entry point
├── iosApp/                             # iOS entry point (Xcode)
├── webApp/                             # Web entry point (Kotlin/Wasm, optional)
└── gradle/
    └── libs.versions.toml              # Version catalog
```

## Compose Multiplatform UI in commonMain

When the project ships one Compose UI tree to all KMP targets (Android + iOS, plus optionally Web/Wasm), each screen-feature module exposes `ui/` and `viewmodel/` as sibling packages under one `commonMain` source set. The platform-app modules (`androidApp/`, `iosApp/`) become thin hosts — navigation graph, DI bootstrap, platform receivers, entry point — and contain no screen-level composables.

```
features/{feature}/
└── src/commonMain/kotlin/com/{org}/{feature}/
    ├── ui/                                     # Compose screens + their helpers
    │   ├── {Screen}Screen.kt                   # Top-level screen composable
    │   ├── {Screen}Formatters.kt               # Pure non-Composable helpers
    │   └── {Type}UiExtensions.kt               # UI-only extensions on shared types
    ├── viewmodel/
    │   ├── {Screen}ViewModel.kt
    │   ├── {Screen}Contract.kt
    │   └── inputhandler/
    │       └── {Action}InputHandler.kt
    └── di/
        └── {Feature}Module.kt
```

Choose this variant when the team wants pixel-identical UI across platforms and the Android/iOS apps would otherwise be near-empty hosts. Choose the platform-native variant from `compose-coding-standards.md` (Compose in `androidApp/`, SwiftUI in `iosApp/`) when each platform's UX must follow its HIG or contains meaningful platform-only surfaces (widgets, complications, deep system integrations).

The rules in `compose-coding-standards.md` ("Compose UI Patterns", "Render Decisions Are Typed Structures (T-013)", "Accessibility", "Performance") apply to both variants. For intra-package layout inside `ui/`, see `compose-coding-standards.md` § "File Organization in `ui/`".

## Clean Architecture Layers

### Dependency Rules (enforced by Konsist)

```
domain  →  depends on NOTHING
data    →  depends on domain
viewmodel → depends on domain
ui      →  depends on domain
sharedPresentation → depends on domain
```

- **domain** is pure Kotlin — no framework dependencies, no platform imports, no Ktor, no Room, no Koin.
- **data** implements domain interfaces. Contains all framework-specific code (Ktor, Room, platform APIs).
- **sharedPresentation** contains ViewModels and InputHandlers. Depends on domain only (use cases, repository interfaces).
- **Platform UI** (Compose, SwiftUI) depends on domain models for display, never on data layer.

### Layer Contracts

- Repository **interfaces** live in `domain`. Implementations live in `data`.
- Use cases live in `domain`. They are the only way ViewModels access business logic.
- DTOs live in `data/remote/`. Domain models live in `domain/model/`. Map between them in `data/mapper/`.
- Never expose data layer types (DTOs, entities, Ktor responses) to the presentation or domain layers.

## MVI Pattern (Model-View-Intent)

### Contract Definitions

Every screen has a dedicated contract file defining its Input, State, and Effect:

```kotlin
// features/{feature}/sharedPresentation/{screen}/viewmodel/{Screen}Contract.kt

/**
 * User actions and events for the notes list screen
 */
sealed interface NotesListInput : Input {
    data object LoadNotes : NotesListInput
    data class DeleteNote(val noteId: String) : NotesListInput {
        override val eventData = mapOf("noteId" to noteId)
    }
    data class SearchNotes(val query: String) : NotesListInput
}

/**
 * Persistent screen state
 */
data class NotesListState(
    val notes: List<Note> = emptyList(),
    val isLoading: Boolean = true,
    val searchQuery: String = "",
    val error: AppError? = null,
) : State {
    override val eventName: String = "NotesListState"
}

/**
 * One-off events (navigation, snackbar, etc.)
 */
sealed interface NotesListEffect : Effect {
    data class NavigateToDetail(val noteId: String) : NotesListEffect {
        override val eventName: String = "NavigateToNoteDetail"
    }
    data class ShowSnackbar(val message: String) : NotesListEffect {
        override val eventName: String = "ShowSnackbar"
    }
}

/**
 * Internal results (reduced into State)
 */
sealed interface NotesListResult : Result {
    data class NotesLoaded(val notes: List<Note>) : NotesListResult
    data class NoteDeleted(val noteId: String) : NotesListResult
    data object Loading : NotesListResult
    data class Error(val error: AppError) : NotesListResult
}
```

Rules:
- `Input` = user actions. `sealed interface` implementing `Input`.
- `State` = persistent screen state. Single `data class` implementing `State`. Must define sensible defaults.
- `Effect` = one-shot events (navigation, toasts). `sealed interface` implementing `Effect`. Never reduced into State.
- `Result` = internal outcomes of processing inputs. `sealed interface` implementing `Result`. Reduced into State by the ViewModel or InputHandlers.
- All `Input`, `State`, and `Effect` types implement `Track` for automatic analytics.
- **`*State` types directly implementing `State` MUST be sealed** (enforced by Konsist rule, T-013 category (a)). Leaf subtypes nested inside a sealed parent are `data class` / `data object`; the parent is `sealed class` or `sealed interface`.
- **`*State` types MUST NOT pack 3+ `show*: Boolean` properties** (enforced by Konsist rule, T-013 category (d)). Three parallel `show*` flags are a mutually-exclusive sub-state in disguise — collapse to a single sealed field. See `shared-standards.md` "UI Render Decisions Belong to Typed Structures" for the framework and `compose-coding-standards.md` "Render Decisions Are Typed Structures (T-013)" for Compose-specific enforcement.

### ViewModel

```kotlin
// features/{feature}/sharedPresentation/{screen}/viewmodel/{Screen}ViewModel.kt

class NotesListViewModel(
    private val getNotesUseCase: GetNotesUseCase,
    private val deleteNoteUseCase: DeleteNoteUseCase,
    analyticsService: AnalyticsService,
) : ViewModel<NotesListInput, NotesListState, NotesListEffect>(
    initialState = NotesListState(),
    inputHandlers = listOf(
        LoadNotesInputHandler(getNotesUseCase),
        DeleteNoteInputHandler(deleteNoteUseCase),
        SearchNotesInputHandler(getNotesUseCase),
    ),
    analyticsService = analyticsService,
)
```

Rules:
- Extend the base `ViewModel<I, S, E>` with the screen's Input, State, Effect types.
- Pass `initialState` with sensible defaults.
- Register all `InputHandler` instances in the `inputHandlers` list.
- ViewModel itself should be thin — delegate logic to InputHandlers.
- Dependencies are use cases and services, never repositories directly (use cases mediate).
- `AnalyticsService` passed to base class for automatic tracking.

### InputHandler

```kotlin
// features/{feature}/sharedPresentation/{screen}/viewmodel/inputhandler/LoadNotesInputHandler.kt

class LoadNotesInputHandler(
    private val getNotesUseCase: GetNotesUseCase,
) : InputHandler<NotesListInput.LoadNotes, NotesListState> {

    override fun clazz() = NotesListInput.LoadNotes::class

    override fun handle(input: NotesListInput.LoadNotes, state: NotesListState): Flow<Result> = flow {
        emit(NotesListResult.Loading)
        getNotesUseCase()
            .onSuccess { notes ->
                emit(NotesListResult.NotesLoaded(notes))
            }
            .onFailure { error ->
                emit(NotesListResult.Error(error.toAppError()))
            }
    }
}
```

Rules:
- One `InputHandler` per `Input` type. Name: `{Action}InputHandler`.
- InputHandlers reside in `viewmodel/inputhandler/` package (enforced by Konsist).
- `clazz()` returns the `KClass` of the specific `Input` this handler processes.
- `handle()` returns a `Flow<Result>` — emit `Result` objects that will be reduced into State or dispatched as Effects.
- Use `makeCancellable(inputClass)` for long-running operations that the user might cancel.
- Use `executeInParallel()` for results that should be processed concurrently.
- InputHandlers receive use cases via constructor, not repositories directly.

### Cancellable and Parallel Flows

```kotlin
// Cancellable flow — user can cancel an ongoing search
override fun handle(input: SearchInput, state: MyState): Flow<Result> = flow {
    emit(SearchResult.Loading)
    val results = searchUseCase(input.query)
    emit(SearchResult.Loaded(results))
}.makeCancellable(SearchInput::class)

// Cancel from UI
viewModel.process(CancelInput(SearchInput::class))

// Parallel execution — results processed concurrently
override fun handle(input: LoadDashboard, state: DashState): Flow<Result> = flow {
    emit(DashResult.Loading)
    val stats = statsUseCase()
    val notifications = notificationsUseCase()
    emit(DashResult.StatsLoaded(stats))
    emit(DashResult.NotificationsLoaded(notifications))
}.executeInParallel()
```

## Use Cases

```kotlin
// features/{feature}/domain/usecase/GetNotesUseCase.kt

class GetNotesUseCase(
    private val notesRepository: NotesRepository,
) {
    suspend operator fun invoke(): Result<List<Note>> =
        notesRepository.getNotes()
}
```

Rules (enforced by Konsist):
- Use case classes reside in `domain..usecase` packages.
- **Single public `operator fun invoke()`** — no other public methods.
- Name: `{Verb}{Entity}UseCase` (e.g., `GetNotesUseCase`, `DeleteNoteUseCase`, `SyncDataUseCase`).
- Returns `Result<T>`, `Flow<T>`, or `Flow<Result<T>>` depending on the operation.
- Orchestrates one or more repositories. Contains business rules that don't belong in a single repository.
- Skip use cases for trivial pass-through operations — use them when there's actual logic to encapsulate or when multiple repositories need coordination.

## Repository Pattern

```kotlin
// domain/repository/NotesRepository.kt (interface in domain)
interface NotesRepository {
    suspend fun getNotes(): Result<List<Note>>
    fun observeNotes(): Flow<List<Note>>
    suspend fun createNote(note: Note): Result<Note>
    suspend fun deleteNote(id: String): Result<Unit>
}

// data/repository/NotesRepositoryImpl.kt (implementation in data)
class NotesRepositoryImpl(
    private val api: NotesApi,
    private val dao: NotesDao,
    private val mapper: NoteMapper,
) : NotesRepository {

    override suspend fun getNotes(): Result<List<Note>> = runCatching {
        val dtos = api.getNotes()
        dtos.map(mapper::toDomain)
    }

    override fun observeNotes(): Flow<List<Note>> =
        dao.observeAll().map { entities -> entities.map(mapper::toDomain) }
}
```

Rules (enforced by Konsist):
- Repository **interfaces** in `domain` with `Repository` suffix.
- Repository **implementations** in `data` with `RepositoryImpl` suffix.
- Repositories return domain models, never DTOs or entities.
- `suspend fun` for one-shot operations, `Flow` for reactive streams.
- Wrap API calls in `runCatching` to return `Result<T>`.

## Data Models & Serialization

```kotlin
// Domain model (domain/model/) — pure, no annotations
data class Note(
    val id: String,
    val title: String,
    val content: String,
    val createdAt: LocalDateTime,
)

// DTO (data/remote/) — serialization annotations
@Serializable
data class NoteDto(
    @SerialName("id") val id: String,
    @SerialName("title") val title: String,
    @SerialName("content") val content: String,
    @SerialName("created_at") val createdAt: String,
)

// Entity (data/local/) — Room/SQLDelight annotations
@Entity(tableName = "notes")
data class NoteEntity(
    @PrimaryKey val id: String,
    val title: String,
    val content: String,
    val createdAt: Long,
)

// Mapper (data/mapper/)
class NoteMapper {
    fun toDomain(dto: NoteDto): Note = Note(
        id = dto.id,
        title = dto.title,
        content = dto.content,
        createdAt = LocalDateTime.parse(dto.createdAt),
    )

    fun toEntity(domain: Note): NoteEntity = NoteEntity(
        id = domain.id,
        title = domain.title,
        content = domain.content,
        createdAt = domain.createdAt.toEpochMilliseconds(),
    )
}
```

Rules:
- **Domain models**: Pure `data class`. No framework annotations. Live in `domain/model/`.
- **DTOs**: `@Serializable` with explicit `@SerialName` on every field. Live in `data/remote/`.
- **Entities**: Room/SQLDelight annotated. Live in `data/local/`.
- **Mappers**: Dedicated mapper classes in `data/mapper/`. Never map inline.
- Three distinct model types. Never reuse a DTO as a domain model.

## Dependency Injection (Koin)

```kotlin
// features/{feature}/data/di/{Feature}DataModule.kt
val notesDataModule = module {
    single<NotesRepository> { NotesRepositoryImpl(get(), get(), get()) }
    factory { NoteMapper() }
}

// features/{feature}/sharedPresentation/di/{Feature}PresentationModule.kt
val notesPresentationModule = module {
    factory { GetNotesUseCase(get()) }
    factory { DeleteNoteUseCase(get()) }
    viewModel { NotesListViewModel(get(), get(), get()) }
}
```

Rules:
- Koin for all DI. One module per layer per feature.
- `single` for singletons (repositories, API clients, database).
- `factory` for stateless objects (use cases, mappers).
- `viewModel` for ViewModels.
- Koin modules are aggregated at the app level and loaded at startup.

## Expect / Actual

```kotlin
// commonMain — expect declaration
expect class SecureStorage {
    suspend fun save(key: String, value: String)
    suspend fun get(key: String): String?
    suspend fun delete(key: String)
}

// androidMain — actual implementation
actual class SecureStorage(private val context: Context) {
    private val prefs = EncryptedSharedPreferences.create(...)

    actual suspend fun save(key: String, value: String) {
        prefs.edit { putString(key, value) }
    }

    actual suspend fun get(key: String): String? =
        prefs.getString(key, null)

    actual suspend fun delete(key: String) {
        prefs.edit { remove(key) }
    }
}

// iosMain — actual implementation
actual class SecureStorage {
    actual suspend fun save(key: String, value: String) {
        NSUserDefaults.standardUserDefaults.setObject(value, forKey = key)
    }
    // ...
}
```

Rules:
- `expect`/`actual` only for genuine platform differences (file system, secure storage, biometrics, platform APIs).
- Define `expect` in `commonMain`. Provide `actual` for every target (`androidMain`, `iosMain`, etc.).
- Never use `expect`/`actual` for things that can be solved with a multiplatform library.
- Platform-specific dependencies only inside `actual` implementations.
- Wrap platform APIs behind domain interfaces so consumers stay platform-agnostic.

## KMP/Web Targets (Kotlin/Wasm & Kotlin/JS)

When targeting the browser via Compose Multiplatform for Web:

### Source Sets

```
src/
├── commonMain/          # Shared logic (all targets)
├── androidMain/         # Android-specific
├── iosMain/             # iOS-specific
├── wasmJsMain/          # Kotlin/Wasm browser target (preferred)
├── jsMain/              # Kotlin/JS fallback (only if Wasm not viable)
└── commonTest/          # Shared tests
```

- **Kotlin/Wasm (`wasmJsMain`)** is the preferred web target — better performance and Compose Multiplatform support.
- **Kotlin/JS (`jsMain`)** is a fallback for libraries or environments that don't support Wasm yet.
- Web-specific `actual` implementations go in `wasmJsMain` or `jsMain`.

### Web-Specific Considerations

- **No JVM APIs** in `commonMain` — avoid `java.*` imports. Use `kotlinx-datetime` instead of `java.time`, `kotlinx-io` instead of `java.io`.
- **Storage**: Use `localStorage` or `IndexedDB` via `expect`/`actual` for the web target. No Room/SQLDelight on web (use an in-memory or IndexedDB-backed solution).
- **Networking**: Ktor client works on all targets including Wasm. The `Js` engine is used for web.
- **Coroutines**: `kotlinx-coroutines-core` works on all targets. Use `Dispatchers.Default` (no `Dispatchers.IO` on web).
- **Serialization**: `kotlinx-serialization` works on all targets unchanged.
- **Binary size**: Be mindful of Wasm binary size — avoid unnecessary dependencies in `commonMain` that bloat the web build. Use Gradle's `wasmJsMain` dependencies sparingly.

### Build Configuration

```kotlin
kotlin {
    androidTarget()
    iosArm64()
    iosSimulatorArm64()
    wasmJs {
        browser {
            commonWebpackConfig {
                outputFileName = "app.js"
            }
        }
    }
    // jsMain only if needed:
    // js(IR) { browser() }
}
```

## Shared Client-Server Code (KMP + Ktor Server)

When the backend uses Ktor (see @.claude/rules/backend/kotlin/ktor-server-coding-standards.md), client and server can share types via a `commonMain` module:

```
project/
├── shared/                     # KMP module — commonMain
│   └── src/commonMain/kotlin/
│       ├── dto/                # Request/response DTOs (client + server)
│       ├── model/              # Domain models
│       ├── validation/         # Shared validation rules
│       └── error/              # Shared error types + ApiResponse envelope
├── server/                     # Ktor server (depends on :shared)
├── androidApp/                 # Android app (depends on :shared)
├── iosApp/                     # iOS app (depends on :shared)
└── webApp/                     # Web app (depends on :shared, if applicable)
```

Rules:
- **Shared DTOs** (`@Serializable`) live in `commonMain` — never duplicate between client and server.
- **Shared validation** runs on both client and server — define once in `commonMain`.
- **Shared error envelope** (`ApiResponse<T>`) ensures consistent shape across all platforms.
- Server and all clients import the shared module as a Gradle dependency.
- See `ktor-server-coding-standards.md` for server-side patterns that consume these shared types.

## Networking (Ktor)

```kotlin
// core/network/ — configured client
val networkModule = module {
    single {
        HttpClient {
            install(ContentNegotiation) { json(Json { ignoreUnknownKeys = true }) }
            install(Logging) { level = LogLevel.BODY }
            install(HttpTimeout) {
                requestTimeoutMillis = 30_000
                connectTimeoutMillis = 10_000
            }
            defaultRequest {
                url(BuildConfig.API_BASE_URL)
                contentType(ContentType.Application.Json)
            }
        }
    }
}

// features/{feature}/data/remote/{Feature}Api.kt
class NotesApi(private val client: HttpClient) {
    suspend fun getNotes(): List<NoteDto> =
        client.get("api/v1/notes").body<ApiResponse<List<NoteDto>>>().data

    suspend fun createNote(request: CreateNoteRequest): NoteDto =
        client.post("api/v1/notes") { setBody(request) }.body<ApiResponse<NoteDto>>().data
}
```

Rules:
- Never expose Ktor types (`HttpClient`, `HttpResponse`) outside the data layer.
- API classes wrap Ktor calls and return DTOs.
- `ApiResponse<T>` envelope parsing at the API layer.
- Configure Ktor client once in `core/network`, inject via Koin.

## Analytics

Every `Input`, `State`, and `Effect` automatically participates in analytics through the `Track` interface:

```kotlin
interface Track {
    val eventData: Map<String, String>  // auto-computed from properties
    val eventName: String               // auto-computed from class name
}
```

- The base `ViewModel` calls `analyticsService.track(input)` on every `process()` call.
- The base `ViewModel` calls `analyticsService.track(result)` on every `Result` that implements `Track`.
- Override `eventName` and `eventData` on specific Inputs/Effects when the auto-computed values aren't suitable.
- Sensitive data (passwords, tokens, PII) MUST be excluded from `eventData` — override with empty map.

## Observability

> **Full reference with code examples:** See `@docs/references/kmp-observability-reference.md`

All observability in KMP uses expect/actual pattern to remain tool-agnostic. Platform actuals delegate to whatever vendor SDK the project has chosen.

### Key Observability Rules

- **Structured Logging**: `expect interface Logger` in `commonMain`. Platform actuals delegate to chosen logging framework. Include `traceId`, `userId`, `module` in context. NEVER log PII, tokens, passwords.
- **Crash Reporting**: `expect interface CrashReporter` in `commonMain`. Install `CoroutineExceptionHandler` at ViewModel scope. Call `setUserId()` on login, `clearCustomKeys()` on logout.
- **Performance Monitoring**: `expect interface PerformanceTrace` in `commonMain`. Instrument critical paths: network calls, DB operations, serialization.
- **Network Observability**: Ktor client plugin for tracing headers, request/response logging (sanitized), and metrics collection.
- All observability interfaces live in `commonMain` — no hardcoded vendor dependencies in shared code.
- Platform implementations injected via Koin or your DI system.
- Reference `@.claude/rules/shared/shared-standards.md` for baseline logging contract.
- Reference `@.claude/rules/shared/operational-standards.md` for SLO definitions and alerting baselines.

## Testing

> **Full reference with code examples:** See `@docs/references/kmp-testing-reference.md`

### Test Types

| Test Type | Framework | Location | Run By |
|-----------|-----------|----------|--------|
| Unit (UseCase, Repository, Mapper) | kotlin.test + Mokkery | `src/commonTest/` | CI (every commit) |
| Unit (InputHandler, ViewModel) | kotlin.test + Mokkery + Turbine | `src/commonTest/` | CI (every commit) |
| Integration (API + DB) | kotlin.test + Ktor MockEngine + Testcontainers | `src/commonTest/` or `src/jvmTest/` | CI (every commit) |
| Screenshot / Visual Regression | Paparazzi (Android), swift-snapshot-testing (iOS) | Platform test dirs | CI (every PR) |
| Performance Benchmarking | kotlinx-benchmark + Jetpack Macrobenchmark (Android) | `benchmark/` module | CI (nightly) |
| Stress / Load | k6 + custom coroutine harness | `stress-tests/` | CI (pre-release) |
| Security | dependency-check + detekt custom rules | `build-logic/` | CI (every PR) |
| Accessibility | Compose semantics assertions + platform tools | Platform test dirs | CI (every PR) + manual |
| Architecture Enforcement | Konsist | `src/test/` | CI (every commit) |

### Key Testing Rules

- **Given / When / Then** structure in every test.
- Use Turbine's `.test {}` for all Flow assertions.
- Use `runTest` for all coroutine tests.
- `FakeTimeService` for deterministic time in tests.
- Test each InputHandler in isolation. Test ViewModels for integration (state transitions).
- When a function maps over a `sealed class` or `enum class` with a `when` expression, the test for that function MUST assert one case per branch. Covering 2 of 5 enum values is a coverage gap, not coverage — a reorder or rename of an unasserted case ships undetected. This applies in particular to functions named `build*Label`, `*ToDomain`, `map*`, and to any `*Mapper.toDomain` / `toPresentation` helper. The number of distinct assertions on the function under test must be `>=` the number of `when` branches.
- Coverage targets: 85%+ on shared code (`commonMain`), 80%+ on ViewModels, 60%+ overall.
- Screenshot tests for every design system component and every screen's 4 states.
- Performance benchmarks must not regress beyond documented thresholds.
- Security tests run on every PR. Load tests run pre-release.
- Accessibility tests are mandatory, not optional.
- Naming convention: `snake_case` with format: `when_<condition>_then_<expected_result>`

### Cross-Platform Testing Coordination

When shared KMP code in `commonMain` is modified, all consuming platforms must verify compatibility before merge. This prevents a change that works on one platform from breaking another.

**Rules:**

- Any PR that modifies `commonMain` code MUST be reviewed and tested by all platform consumers:
  - @Swift (iOS) — run iOS tests, verify KMP framework builds, check expect/actual compatibility.
  - @Kai (Android) — run Android tests, verify Gradle sync, check Hilt/Koin bridge.
  - @Nova (Web, if applicable) — run web target tests, verify Wasm/JS build.
  - @Link (Ktor server, if applicable) — run server tests, verify shared DTO/validation compatibility.

- **Sign-off requirement**: The PR must have explicit approval from at least the iOS and Android consumers (the primary KMP targets). Web and server consumers sign off if they depend on the changed module.

- **CI enforcement**: The PR checks workflow must build and test all targets. A `commonMain` change that passes Android tests but fails iOS tests is not mergeable.

- **Expect/actual changes**: Any modification to an `expect` declaration requires corresponding `actual` updates across all platform source sets. The PR author is responsible for updating all actuals, or coordinating with the platform agent who owns the actual.

- **Breaking changes in shared modules**: If a change to `commonMain` requires consuming platform code to change (e.g., new required parameter, renamed class, changed return type):
  1. The PR author notifies all consumers via @Atlas.
  2. Platform agents update their code on the same branch or coordinated branches.
  3. All platform builds must pass before merge.

- **Shared DTO/validation changes**: If shared DTOs or validation rules are modified, both the Ktor server (if applicable) and all client platforms must verify. Compile-time safety covers type changes, but behavioral changes in validation logic require explicit test verification on both server and client.

**Coordination flow:**

```
Link modifies commonMain
  ├── Opens PR, tags @Swift @Kai @Nova (if web target exists)
  ├── CI builds all targets (Android, iOS, Web, Server)
  ├── @Swift runs iOS-specific integration tests
  ├── @Kai runs Android-specific integration tests
  ├── Both approve (or request changes)
  └── Merge only after all platform approvals + CI green
```

## Architecture Enforcement (Konsist)

Konsist tests enforce architectural rules at compile/test time:

```kotlin
// Enforced rules:
// 1. UseCase classes reside in domain..usecase packages
// 2. UseCase classes expose a single public invoke()
// 3. InputHandler classes reside in viewmodel..inputhandler packages
// 4. InputHandler classes have 'InputHandler' suffix
// 5. Repository interfaces are in domain layer with 'Repository' suffix
// 6. RepositoryImpl classes are in data layer
// 7. Clean architecture layer dependencies are correct
// 8. T-013(a): Classes directly implementing architecture's State must be sealed
// 9. T-013(d): *State classes must not declare 3+ show* Boolean flags
```

Two further T-013 rules (b: `is *PM` discriminator in feature UI; c: variant Boolean param on design-system Composable) are implemented as custom Detekt rules in `build-logic/detekt-rules/` rather than Konsist, because they require AST-level inspection that Konsist's class-shape API does not support. See `compose-coding-standards.md` "Render Decisions Are Typed Structures (T-013)" for the full enforcement matrix.

- Konsist tests live in a dedicated test module or in `src/test/`.
- Run as part of CI — architecture violations fail the build.
- Add new Konsist rules when new architectural patterns are introduced.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Modules | `kebab-case` | `features/notes/domain` |
| Packages | `lowercase` | `com.example.app.features.notes.domain.usecase` |
| Classes | `PascalCase` + layer suffix | `NotesRepositoryImpl`, `GetNotesUseCase` |
| Interfaces | `PascalCase`, no `I` prefix | `NotesRepository`, `AnalyticsService` |
| Functions | `camelCase`, verb-first | `getNotes()`, `observeAll()` |
| Properties | `camelCase` | `isLoading`, `noteId` |
| Test methods | `snake_case`: `when_x_then_y` | `when_load_notes_then_emit_success` |
| Inputs | `PascalCase`, action-noun | `LoadNotes`, `DeleteNote` |
| Effects | `PascalCase`, event-description | `NavigateToDetail`, `ShowSnackbar` |
| Results | `PascalCase`, outcome-noun | `NotesLoaded`, `Loading`, `Error` |
| States | `{Screen}State` | `NotesListState` |
| InputHandlers | `{Action}InputHandler` | `LoadNotesInputHandler` |
| Koin modules | `{feature}{Layer}Module` | `notesDataModule`, `notesPresentationModule` |

## Kotlin Code Style

- **Indentation**: 4 spaces.
- **Line length**: 120–140 characters.
- **Imports**: Sorted alphabetically. Standard library → third-party → project.
- **KDoc**: Required on all public APIs. Sparse comments elsewhere.
- **No `!!`** in production code.
- **`val` over `var`** — immutability by default.
- **`data class`** for all models, DTOs, states.
- **`sealed interface`** for all type hierarchies (Input, Effect, Result, errors).

## Build Configuration

```kotlin
// build-logic convention plugin usage
plugins {
    id("playground.multiplatform.lib")   // KMP library module setup
    id("playground.testing")             // kotlin.test + Mokkery + Turbine + coroutines-test
    id("playground.koin")                // Koin DI
    id("playground.room")               // Room database (if needed)
    id("playground.compose.multiplatform") // Compose Multiplatform (if UI)
    id("playground.detekt")             // Static analysis
    id("playground.koverage")           // Code coverage
}
```

- **Java 21** required. Set `JAVA_HOME` or configure IDE.
- **Version catalog** (`libs.versions.toml`) for all dependencies.
- **Convention plugins** in `build-logic/plugins/` for consistent module setup.
- **Configuration cache** and **build cache** enabled.
- Modules must build independently — no circular module dependencies.
- **JetBrains Kotlin skills for build/tooling migrations** (see @.claude/rules/shared/kotlin-agent-skills.md): AGP 9.0+ upgrades → `kotlin-tooling-agp9-migration`; CocoaPods → Swift Package Manager → `kotlin-tooling-cocoapods-spm-migration`; `kotlinx.collections.immutable` 0.5.x bumps → `kotlin-tooling-immutable-collections-0-5-x-migration`. Invoke the matching skill before performing the migration.

## Platform Integration

### Android Consumer (Kai)

```kotlin
// In Compose screen
@Composable
fun NotesListScreen(
    viewModel: NotesListViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        viewModel.effect.collect { effect ->
            when (effect) {
                is NotesListEffect.NavigateToDetail -> navController.navigate(...)
                is NotesListEffect.ShowSnackbar -> snackbarHostState.showSnackbar(effect.message)
            }
        }
    }

    // Render based on state...
    viewModel.process(NotesListInput.LoadNotes)
}
```

### iOS Consumer (Swift)

```swift
// In SwiftUI view — observe KMP ViewModel via SKIE or manual Flow collection
struct NotesListScreen: View {
    @StateObject private var viewModel = NotesListViewModelWrapper()

    var body: some View {
        // Map KMP State to SwiftUI view
    }
}
```

### Web Consumer (Nova — Kotlin/Wasm)

```kotlin
// In Compose for Web screen
@Composable
fun NotesListScreen(
    viewModel: NotesListViewModel = koinInject(),
) {
    val state by viewModel.state.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.effect.collect { effect ->
            when (effect) {
                is NotesListEffect.NavigateToDetail -> /* browser routing */ Unit
                is NotesListEffect.ShowSnackbar -> /* web notification */ Unit
            }
        }
    }

    // Render based on state (Compose Multiplatform UI)...
    viewModel.process(NotesListInput.LoadNotes)
}
```

- KMP ViewModels are consumed directly on Android via `koinViewModel()`.
- On iOS, wrap KMP ViewModels in a Swift `ObservableObject` or use SKIE for native Flow interop.
- On Web (Wasm), consume via `koinInject()` and `collectAsState()` in Compose Multiplatform for Web.
- Never import platform-specific code in `commonMain`.
- Follow Link's integration guides for each KMP module.

### Platform-Specific UI Standards

Each platform has dedicated UI coding standards that complement this KMP guide:

- **Android**: @.claude/rules/mobile/android/compose-coding-standards.md — Jetpack Compose, Android-specific DI (Hilt), Retrofit networking, testing with Robolectric/MockWebServer.
- **iOS**: @.claude/rules/mobile/ios/swiftui-coding-standards.md — SwiftUI, async/await patterns, URLSession, testing with XCTest, VoiceOver accessibility.
- **Web**: Compose Multiplatform for Web targets (Kotlin/Wasm) — follow the core Compose patterns with platform-specific event handling and styling.

These standards should be read alongside the shared KMP standards. Link coordinates shared code; Kai and Swift ensure platform integration is idiomatic for their respective platforms.
