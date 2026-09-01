# Kotlin Multiplatform (KMP) Coding Standards

> **How to read this file.** This standard is **not preloaded** into the session — read it on demand when your task is in this stack.
> Path: `${CLAUDE_PLUGIN_ROOT}/rules/mobile/shared/kmp-coding-standards.md`, falling back to `.claude/rules/mobile/shared/kmp-coding-standards.md` when `CLAUDE_PLUGIN_ROOT` is unset.

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
    data class OpenNote(val noteId: String) : NotesListInput {
        override val eventData = mapOf("noteId" to noteId)
    }
}

/**
 * Persistent screen state — one leaf per screen shape (T-013 category (a)).
 * The screen root renders with an exhaustive `when (state)`; there are no
 * `isLoading` / `error != null` / `isEmpty()` flag combinations to reconcile.
 */
sealed interface NotesListState : State {
    /** Analytics name. Leaves override it when finer granularity is wanted. */
    override val eventName: String get() = "NotesListState"

    data object Loading : NotesListState

    data object Empty : NotesListState

    data class Error(val error: AppError) : NotesListState {
        override val eventName: String = "NotesListState.Error"
    }

    data class Loaded(
        val notes: List<Note>,
        val searchQuery: String = "",
    ) : NotesListState
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
- `State` = persistent screen state. A `sealed interface` (or `sealed class`) implementing `State`, with one `data class` / `data object` leaf per screen shape — typically `Loading`, `Empty`, `Error`, `Loaded`. A single `data class` carrying `isLoading` / `error` / emptiness flags is the T-013 category (a) anti-pattern and is rejected by the Konsist rule below.
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
    initialState = NotesListState.Loading,
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
- Pass `initialState` — the sealed leaf the screen opens in, usually `Loading`. Never a flag-bearing `data class`.
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

## Platform Abstractions: Interface + DI (preferred) vs Expect / Actual

An `actual` declaration must match its `expect` **exactly**, constructor included. The moment one platform needs a dependency the other does not — Android's `Context` is the usual case — `expect class` stops working: `commonMain` has no way to supply the argument, and the two actuals cannot legally differ in their constructor signature.

The working pattern is a plain `interface` in `commonMain` plus platform implementations bound through Koin. Use it for anything that carries platform dependencies.

```kotlin
// commonMain — a plain interface. No expect, no constructor to reconcile.
interface SecureStorage {
    suspend fun save(key: String, value: String)
    suspend fun get(key: String): String?
    suspend fun delete(key: String)
}
```

```kotlin
// androidMain — Android Keystore-backed EncryptedSharedPreferences
class AndroidSecureStorage(context: Context) : SecureStorage {

    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs = EncryptedSharedPreferences.create(
        context,
        "secure_storage",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    override suspend fun save(key: String, value: String) = withContext(Dispatchers.IO) {
        prefs.edit { putString(key, value) }
    }

    override suspend fun get(key: String): String? = withContext(Dispatchers.IO) {
        prefs.getString(key, null)
    }

    override suspend fun delete(key: String) = withContext(Dispatchers.IO) {
        prefs.edit { remove(key) }
    }
}
```

```kotlin
// iosMain — Keychain. NEVER NSUserDefaults: it is a plaintext plist, is
// included in device backups, and is readable by anyone with file access.
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.MemScope
import kotlinx.cinterop.alloc
import kotlinx.cinterop.convert
import kotlinx.cinterop.memScoped
import kotlinx.cinterop.ptr
import kotlinx.cinterop.value
import platform.CoreFoundation.CFDictionaryAddValue
import platform.CoreFoundation.CFDictionaryCreateMutable
import platform.CoreFoundation.CFMutableDictionaryRef
import platform.CoreFoundation.CFRelease
import platform.CoreFoundation.CFStringRef
import platform.CoreFoundation.CFTypeRefVar
import platform.CoreFoundation.kCFAllocatorDefault
import platform.CoreFoundation.kCFBooleanTrue
import platform.CoreFoundation.kCFTypeDictionaryKeyCallBacks
import platform.CoreFoundation.kCFTypeDictionaryValueCallBacks
import platform.Foundation.CFBridgingRelease
import platform.Foundation.CFBridgingRetain
import platform.Foundation.NSData
import platform.Foundation.NSString
import platform.Foundation.NSUTF8StringEncoding
import platform.Foundation.create
import platform.Foundation.dataUsingEncoding
import platform.Security.*

@OptIn(ExperimentalForeignApi::class)
class IosSecureStorage(
    private val service: String,
) : SecureStorage {

    override suspend fun save(key: String, value: String): Unit = memScoped {
        // The Keychain has no upsert — replacing an item is delete-then-add.
        delete(key)

        val data = (value as NSString).dataUsingEncoding(NSUTF8StringEncoding)
            ?: error("Keychain value for '$key' is not valid UTF-8")

        val attributes = newQuery(capacity = 5)
        CFDictionaryAddValue(attributes, kSecClass, kSecClassGenericPassword)
        attributes.putBridged(kSecAttrService, service)
        attributes.putBridged(kSecAttrAccount, key)
        attributes.putBridged(kSecValueData, data)
        // Device-only: never synced to iCloud, never restored to another device.
        CFDictionaryAddValue(
            attributes,
            kSecAttrAccessible,
            kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        )

        val status = SecItemAdd(attributes, null)
        CFRelease(attributes)
        check(status == errSecSuccess) { "Keychain add failed for '$key' (OSStatus $status)" }
    }

    override suspend fun get(key: String): String? = memScoped {
        val query = newQuery(capacity = 5)
        CFDictionaryAddValue(query, kSecClass, kSecClassGenericPassword)
        query.putBridged(kSecAttrService, service)
        query.putBridged(kSecAttrAccount, key)
        CFDictionaryAddValue(query, kSecReturnData, kCFBooleanTrue)
        CFDictionaryAddValue(query, kSecMatchLimit, kSecMatchLimitOne)

        val result = alloc<CFTypeRefVar>()
        val status = SecItemCopyMatching(query, result.ptr)
        CFRelease(query)

        when (status) {
            errSecSuccess -> (CFBridgingRelease(result.value) as? NSData)
                ?.let { NSString.create(it, NSUTF8StringEncoding) as String? }
            errSecItemNotFound -> null
            else -> error("Keychain read failed for '$key' (OSStatus $status)")
        }
    }

    override suspend fun delete(key: String): Unit = memScoped {
        val query = newQuery(capacity = 3)
        CFDictionaryAddValue(query, kSecClass, kSecClassGenericPassword)
        query.putBridged(kSecAttrService, service)
        query.putBridged(kSecAttrAccount, key)

        val status = SecItemDelete(query)
        CFRelease(query)
        check(status == errSecSuccess || status == errSecItemNotFound) {
            "Keychain delete failed for '$key' (OSStatus $status)"
        }
    }
}

@OptIn(ExperimentalForeignApi::class)
private fun MemScope.newQuery(capacity: Int): CFMutableDictionaryRef? =
    CFDictionaryCreateMutable(
        kCFAllocatorDefault,
        capacity.convert(),
        kCFTypeDictionaryKeyCallBacks.ptr,
        kCFTypeDictionaryValueCallBacks.ptr,
    )

/** Adds an Obj-C value, balancing the +1 that `CFBridgingRetain` takes. */
@OptIn(ExperimentalForeignApi::class)
private fun CFMutableDictionaryRef?.putBridged(key: CFStringRef?, value: Any) {
    val cfValue = CFBridgingRetain(value)
    CFDictionaryAddValue(this, key, cfValue)
    CFRelease(cfValue)
}
```

Binding happens in the platform Koin module — the one place a legitimate `expect`/`actual` seam lives, because a `Module` value has no constructor to vary:

```kotlin
// commonMain
expect val platformModule: Module

// androidMain
actual val platformModule = module {
    single<SecureStorage> { AndroidSecureStorage(androidContext()) }
}

// iosMain
actual val platformModule = module {
    single<SecureStorage> { IosSecureStorage(service = "com.example.app.secure") }
}
```

Rules:
- **Prefer `interface` in `commonMain` + platform classes bound via Koin.** Reach for `expect`/`actual` only when the declaration's signature is genuinely identical on every target (top-level functions, value declarations like `platformModule`, typealiases).
- **`actual` declarations cannot vary their constructor.** If one platform needs a `Context`, a `service` name, or any other platform-only dependency, `expect class` is the wrong tool — that dependency must be injected, which means an interface.
- **A platform implementation must meet the security bar of the strongest platform.** When one platform stores something encrypted and hardware-backed (Android Keystore / EncryptedSharedPreferences), every other platform must reach an equivalent bar (iOS Keychain, Web `IndexedDB` behind Web Crypto with a non-extractable key). Never let one target quietly downgrade to plaintext (`NSUserDefaults`, `SharedPreferences`, `localStorage`) — the abstraction's name promises the guarantee on every target, and the weakest implementation is the one an attacker uses.
- Never use `expect`/`actual` for something a multiplatform library already solves.
- Platform-specific dependencies live only inside platform source sets — never leak `Context`, `NSData`, or a `CFDictionaryRef` across an interface boundary.
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

- **Structured Logging**: a plain `interface Logger` in `commonMain`, plus `expect fun createLogger(module: String): Logger` as the only expect/actual seam. Each platform's `actual createLogger` returns a class implementing the shared interface by delegating to the chosen logging framework. (An `expect interface` would require an `actual interface` per target, which the delegating class could not then implement.) Include `traceId`, `userId`, `module` in context. NEVER log PII, tokens, passwords.
- **Crash Reporting**: plain `interface CrashReporter` + `expect fun getCrashReporter(): CrashReporter`. Install `CoroutineExceptionHandler` at ViewModel scope. Call `setUserId()` on login, `clearCustomKeys()` on logout.
- **Performance Monitoring**: plain `interface PerformanceTrace` + `expect fun getPerformanceTrace(): PerformanceTrace`. Instrument critical paths: network calls, DB operations, serialization.
- **No `java.*` / `System.*` in any of it** — these interfaces and their shared-code callers compile for iOS and Wasm too. `kotlin.time.TimeSource` for elapsed time, `kotlinx.datetime.Clock` for timestamps.
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
    onNavigateToDetail: (String) -> Unit = {},
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    // Effects are one-shot — collected in a LaunchedEffect, never in the body.
    LaunchedEffect(Unit) {
        viewModel.effect.collect { effect ->
            when (effect) {
                is NotesListEffect.NavigateToDetail -> onNavigateToDetail(effect.noteId)
                is NotesListEffect.ShowSnackbar -> snackbarHostState.showSnackbar(effect.message)
            }
        }
    }

    // Inputs are dispatched from effects/callbacks — never from the composition
    // body, which re-runs on every recomposition.
    LaunchedEffect(Unit) { viewModel.process(NotesListInput.LoadNotes) }

    NotesListContent(
        state = state,
        snackbarHostState = snackbarHostState,
        process = viewModel::process,
    )
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
    // Same Content, same signature as the Android host — material3's
    // SnackbarHostState is multiplatform, so the web host owns one too.
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(Unit) {
        viewModel.effect.collect { effect ->
            when (effect) {
                is NotesListEffect.NavigateToDetail -> /* browser routing */ Unit
                is NotesListEffect.ShowSnackbar -> snackbarHostState.showSnackbar(effect.message)
            }
        }
    }

    LaunchedEffect(Unit) { viewModel.process(NotesListInput.LoadNotes) }

    // Render based on state (Compose Multiplatform UI)...
    NotesListContent(
        state = state,
        snackbarHostState = snackbarHostState,
        process = viewModel::process,
    )
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

## Tooling: Android CLI & Agent Skills

Link has access to **vendored Agent Skills** (in `.claude/skills/`) and the **`android` CLI** (via Bash). They **complement** these standards — on conflict, this document and the KMP architecture rules win.

### Kotlin Agent Skills (JetBrains)

When a task matches, `Read` the named `SKILL.md` and follow its workflow:

| Task | Skill (`.claude/skills/…/SKILL.md`) |
|---|---|
| Converting Java sources to idiomatic Kotlin (framework-aware) | `kotlin-tooling-java-to-kotlin` |
| Migrating a KMP project to AGP 9 (`com.android.kotlin.multiplatform.library`, module split, DSL) | `kotlin-tooling-agp9-migration` |
| Migrating KMP iOS interop from CocoaPods to Swift Package Manager | `kotlin-tooling-cocoapods-spm-migration` |

The AGP 9 / KMP upgrade skill is the canonical reference for the Kotlin-version-and-AGP coordination that Link owns (see `operational-standards.md` "Dependency Management"); coordinate cross-platform verification with @Swift and @Kai per the "Cross-Platform Testing Coordination" rules above.

### `android` CLI for the Compose-MP / Android target

For Compose Multiplatform or shared-code work that needs a running Android target, use the `android` CLI via Bash (`android emulator start`, `android run --apks=…`, `android docs search "<keywords>"` for up-to-date Android API guidance, `android layout`/`android screen capture` for inspection). If `command -v android` is empty the toolchain isn't installed — flag it as a blocker (install steps in `/setup-repo`). Android-platform UI tasks (theming, edge-to-edge, navigation, profiling) are owned by Kai and mapped to `android-*` skills in `compose-coding-standards.md`.

Provenance and full inventory: `.claude/skills/VENDORED-SKILLS.md`. Integration overview: `docs/references/android-kotlin-skills-integration.md`.
