# SwiftUI / iOS Coding Standards

Owner: Swift. All iOS code MUST follow these standards. For shared KMP architecture (MVI pattern, Clean Architecture layers, use cases, repositories, data models, Konsist enforcement), see @.claude/rules/mobile/shared/kmp-coding-standards.md — those rules apply here.

**Reading Guide**: iOS development requires reading BOTH documents:
1. **KMP standards** (@.claude/rules/mobile/shared/kmp-coding-standards.md) — the foundation: architecture, MVI pattern, shared code structure, cross-platform testing
2. **This SwiftUI standards document** — iOS-specific layer: SwiftUI UI patterns, URLSession networking, async/await, iOS testing frameworks, accessibility with VoiceOver

## Project Structure

```
App/
├── App/
│   ├── {App}App.swift              # @main entry point
│   ├── AppDelegate.swift           # UIKit bridge (push notifications, etc.)
│   └── DI/
│       └── DependencyContainer.swift  # Dependency registration
├── Features/                       # Feature modules (domain-driven)
│   └── {Feature}/
│       ├── Views/
│       │   ├── {Feature}Screen.swift      # Top-level screen view
│       │   └── {SubComponent}View.swift   # Subviews
│       ├── ViewModels/
│       │   └── {Feature}ViewModel.swift
│       ├── Models/
│       │   └── {Feature}Model.swift       # Feature-specific domain models
│       └── Tests/
│           ├── {Feature}ViewModelTests.swift
│           └── {Feature}UITests.swift
├── Core/                           # Shared infrastructure
│   ├── Networking/
│   │   ├── APIClient.swift         # Configured URLSession / shared KMP client
│   │   ├── APIError.swift          # Typed error hierarchy
│   │   └── Endpoints/
│   │       └── {Resource}Endpoint.swift
│   ├── Persistence/
│   │   ├── KeychainManager.swift
│   │   └── UserDefaultsManager.swift
│   ├── Extensions/                 # Swift/SwiftUI extensions
│   ├── Utilities/                  # Pure helper functions
│   └── DI/
│       └── Protocols/              # Service protocols for DI
├── DesignSystem/                   # Reusable UI components
│   ├── Components/
│   │   ├── Buttons/
│   │   │   └── PrimaryButton.swift
│   │   ├── Cards/
│   │   ├── Inputs/
│   │   └── Feedback/               # Toasts, alerts, empty states
│   ├── Tokens/
│   │   ├── Colors.swift             # Color tokens from Pixel
│   │   ├── Typography.swift         # Font styles
│   │   └── Spacing.swift            # Spacing constants
│   └── Modifiers/
│       └── AccessibilityModifiers.swift
├── Resources/
│   ├── Assets.xcassets
│   ├── Localizable.xcstrings
│   └── Info.plist
└── Shared/                         # KMP integration layer
    └── KMP/
        └── {Module}Bridge.swift    # Swift wrappers around KMP shared code
```

## Layering Rules

Screen (View) → ViewModel → Service/Repository. Never skip layers.

- **View (Screen)**: Layout and presentation only. Binds to ViewModel's `@Published` properties. No business logic, no direct networking, no persistence. Handles navigation via `NavigationStack` / `NavigationPath`.
- **ViewModel**: Business logic, state management, data orchestration. `@MainActor`, `ObservableObject`. Calls services/repositories, publishes state. No SwiftUI imports (except `Foundation` + `Combine`).
- **Service / Repository**: Data access layer. Networking, persistence, KMP bridge calls. Returns domain models. No UI concerns.
- **DesignSystem**: Pure presentational components. No data fetching, no ViewModel references. Props in, views out.

Dependency direction: View → ViewModel → Service → Network/Persistence/KMP. No reverse imports.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files | `PascalCase.swift` | `UserListScreen.swift` |
| Types / Structs / Classes | `PascalCase` | `UserListViewModel` |
| Protocols | `PascalCase` + `-able`/`-ing`/`-Protocol` | `UserFetchable`, `AuthService` |
| Functions / Methods | `camelCase`, verb-first | `fetchUsers()`, `deleteAccount()` |
| Properties | `camelCase` | `isLoading`, `userName` |
| Constants | `camelCase` (static let) | `static let maxRetryCount = 3` |
| Enum cases | `camelCase` | `.loading`, `.error(AppError)` |
| Views (screens) | `{Feature}Screen` | `UserListScreen` |
| Views (components) | `{Name}View` | `UserRowView` |
| ViewModels | `{Feature}ViewModel` | `UserListViewModel` |
| Design system | `{Purpose}{Type}` | `PrimaryButton`, `CardContainer` |

## Swift Conventions

### Optionals — No Force Unwraps

```swift
// GOOD — optional binding
guard let user = currentUser else {
    showLoginScreen()
    return
}

// GOOD — nil coalescing
let displayName = user.name ?? "Anonymous"

// GOOD — optional chaining
let city = user.address?.city

// BAD — force unwrap (NEVER do this)
let name = user.name!
```

- No `!` force unwraps anywhere in production code. Only acceptable in tests with clear assertion context.
- Use `guard let` for early returns, `if let` for conditional branches.
- Use `??` with sensible defaults.

### Value Types First

```swift
// GOOD — struct for models
struct User: Identifiable, Codable, Hashable {
    let id: UUID
    let name: String
    let email: String
    let createdAt: Date
}

// Class only when needed: ObservableObject, reference semantics, inheritance
@MainActor
final class UserListViewModel: ObservableObject { ... }
```

- Prefer `struct` over `class`. Use `class` only for ViewModels (`ObservableObject`) and cases requiring reference semantics.
- Mark classes `final` unless designed for inheritance.
- All ViewModels are `@MainActor` and `final`.

### Access Control

- Default to `private` for properties and methods. Widen only when needed.
- `private(set)` for properties that are read externally but written internally.
- `internal` (default) for types used within the module.
- `public` only for framework/package APIs.

```swift
final class UserListViewModel: ObservableObject {
    @Published private(set) var users: [User] = []
    @Published private(set) var isLoading = false
    @Published private(set) var error: AppError?

    private let userService: UserServiceProtocol

    init(userService: UserServiceProtocol) {
        self.userService = userService
    }
}
```

## View Patterns

### Screen Structure

```swift
struct UserListScreen: View {
    @StateObject private var viewModel: UserListViewModel

    init(userService: UserServiceProtocol = UserService()) {
        _viewModel = StateObject(wrappedValue: UserListViewModel(userService: userService))
    }

    var body: some View {
        content
            .navigationTitle("Users")
            .task { await viewModel.loadUsers() }
            .refreshable { await viewModel.refresh() }
            .alert(
                "Error",
                isPresented: $viewModel.showError,
                presenting: viewModel.error
            ) { _ in
                Button("Retry") { Task { await viewModel.loadUsers() } }
                Button("Cancel", role: .cancel) { }
            } message: { error in
                Text(error.localizedDescription)
            }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .loading:
            ProgressView()
        case .empty:
            ContentUnavailableView("No Users", systemImage: "person.3")
        case .error(let error):
            ErrorStateView(error: error) {
                Task { await viewModel.loadUsers() }
            }
        case .loaded(let users):
            List(users) { user in
                UserRowView(user: user)
            }
        }
    }
}
```

Rules:
- Extract subviews with `@ViewBuilder` private computed properties for readability.
- Prefer `@StateObject` for owned ViewModels, `@ObservedObject` for injected ones.
- Use `.task {}` for async work on appear (auto-cancelled on disappear).
- Use `.refreshable {}` for pull-to-refresh.

### View Composition

- Keep `body` under ~30 lines. Extract subviews.
- Each screen in its own file. Subviews can be `private` structs in the same file if small, or separate files if reused.
- Preview at the bottom of every View file:

```swift
#Preview {
    NavigationStack {
        UserListScreen(userService: MockUserService())
    }
}
```

## ViewModel Pattern

```swift
@MainActor
final class UserListViewModel: ObservableObject {
    enum State: Equatable {
        case loading
        case loaded([User])
        case empty
        case error(AppError)
    }

    @Published private(set) var state: State = .loading
    @Published var showError = false

    var error: AppError? {
        if case .error(let err) = state { return err }
        return nil
    }

    private let userService: UserServiceProtocol
    private var loadTask: Task<Void, Never>?

    init(userService: UserServiceProtocol) {
        self.userService = userService
    }

    func loadUsers() async {
        state = .loading
        do {
            let users = try await userService.fetchUsers()
            state = users.isEmpty ? .empty : .loaded(users)
        } catch let error as AppError {
            state = .error(error)
            showError = true
        } catch {
            state = .error(.unexpected(error))
            showError = true
        }
    }

    func refresh() async {
        await loadUsers()
    }

    func deleteUser(_ user: User) async {
        do {
            try await userService.deleteUser(id: user.id)
            if case .loaded(var users) = state {
                users.removeAll { $0.id == user.id }
                state = users.isEmpty ? .empty : .loaded(users)
            }
        } catch {
            showError = true
        }
    }
}
```

Rules:
- `@MainActor` on all ViewModels — UI state updates must be on main thread.
- Use a `State` enum for screen state — never multiple booleans (`isLoading`, `hasError`, `isEmpty`).
- `@Published private(set)` — views observe but never mutate directly.
- Cancel in-flight tasks when starting new ones (`loadTask?.cancel()`).
- Dependencies injected via `init` for testability.

## Every Screen Must Handle 4 States

Loading, loaded (success), empty, and error. No exceptions. Use the `State` enum pattern above.

```swift
// ContentUnavailableView for empty states (iOS 17+)
ContentUnavailableView("No Results", systemImage: "magnifyingglass", description: Text("Try a different search"))

// Custom ErrorStateView for errors
ErrorStateView(error: error, retryAction: { Task { await viewModel.loadUsers() } })
```

## Error Handling

```swift
// Core/Networking/APIError.swift
enum AppError: Error, Equatable, LocalizedError {
    case networkUnavailable
    case unauthorized
    case notFound(String)
    case serverError(Int, String)
    case decodingFailed
    case unexpected(Error)

    var errorDescription: String? {
        switch self {
        case .networkUnavailable: "No internet connection"
        case .unauthorized: "Please sign in again"
        case .notFound(let entity): "\(entity) not found"
        case .serverError(_, let message): message
        case .decodingFailed: "Something went wrong"
        case .unexpected: "An unexpected error occurred"
        }
    }

    // Equatable conformance for State enum
    static func == (lhs: AppError, rhs: AppError) -> Bool {
        lhs.errorDescription == rhs.errorDescription
    }
}
```

- Typed error enum — never catch generic `Error` and show `localizedDescription` to users.
- Map API errors to `AppError` at the networking layer.
- User-facing messages: friendly, no technical details. Log full error for debugging.

## Networking

### Async/Await + Codable

```swift
// Core/Networking/APIClient.swift
protocol APIClientProtocol {
    func request<T: Decodable>(_ endpoint: Endpoint) async throws -> T
}

final class APIClient: APIClientProtocol {
    private let session: URLSession
    private let decoder: JSONDecoder

    init(session: URLSession = .shared) {
        self.session = session
        self.decoder = JSONDecoder()
        self.decoder.keyDecodingStrategy = .convertFromSnakeCase
        self.decoder.dateDecodingStrategy = .iso8601
    }

    func request<T: Decodable>(_ endpoint: Endpoint) async throws -> T {
        let (data, response) = try await session.data(for: endpoint.urlRequest)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AppError.unexpected(URLError(.badServerResponse))
        }

        switch httpResponse.statusCode {
        case 200...299:
            let envelope = try decoder.decode(ApiResponse<T>.self, from: data)
            return envelope.data
        case 401:
            throw AppError.unauthorized
        case 404:
            throw AppError.notFound(endpoint.resourceName)
        default:
            let errorBody = try? decoder.decode(ErrorResponse.self, from: data)
            throw AppError.serverError(
                httpResponse.statusCode,
                errorBody?.error.message ?? "Server error"
            )
        }
    }
}
```

### Endpoint Pattern

```swift
struct Endpoint {
    let path: String
    let method: HTTPMethod
    let body: Encodable?
    let queryItems: [URLQueryItem]
    let resourceName: String

    var urlRequest: URLRequest {
        var components = URLComponents(string: "\(baseURL)\(path)")!
        if !queryItems.isEmpty { components.queryItems = queryItems }
        var request = URLRequest(url: components.url!)
        request.httpMethod = method.rawValue
        if let body {
            request.httpBody = try? JSONEncoder().encode(body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        return request
    }
}

// Usage
extension Endpoint {
    static func users(cursor: String? = nil, limit: Int = 20) -> Endpoint {
        Endpoint(
            path: "/api/v1/users",
            method: .get,
            body: nil,
            queryItems: [
                cursor.map { URLQueryItem(name: "cursor", value: $0) },
                URLQueryItem(name: "limit", value: "\(limit)"),
            ].compactMap { $0 },
            resourceName: "User"
        )
    }
}
```

Rules:
- `async/await` for all networking. No completion handlers.
- `Codable` for all request/response models.
- `JSONDecoder` configured once: `.convertFromSnakeCase`, `.iso8601`.
- Map HTTP status codes to `AppError` at the API client level.
- Protocol (`APIClientProtocol`) for testability.

## Navigation

### NavigationStack + NavigationPath

```swift
// App-level or feature-level coordinator
@MainActor
final class NavigationCoordinator: ObservableObject {
    @Published var path = NavigationPath()

    func navigateToUser(_ user: User) {
        path.append(user)
    }

    func navigateToSettings() {
        path.append(Route.settings)
    }

    func popToRoot() {
        path = NavigationPath()
    }
}

// In the root view
NavigationStack(path: $coordinator.path) {
    UserListScreen()
        .navigationDestination(for: User.self) { user in
            UserDetailScreen(user: user)
        }
        .navigationDestination(for: Route.self) { route in
            switch route {
            case .settings: SettingsScreen()
            }
        }
}
```

- `NavigationStack` for all navigation (not deprecated `NavigationView`).
- Programmatic navigation via `NavigationPath` for deep links and coordinator patterns.
- Type-safe destinations via `.navigationDestination(for:)`.

## Dependency Injection

Protocol-based injection via init:

```swift
// Protocol
protocol UserServiceProtocol {
    func fetchUsers() async throws -> [User]
    func deleteUser(id: UUID) async throws
}

// Production implementation
final class UserService: UserServiceProtocol {
    private let apiClient: APIClientProtocol

    init(apiClient: APIClientProtocol = APIClient()) {
        self.apiClient = apiClient
    }

    func fetchUsers() async throws -> [User] {
        try await apiClient.request(.users())
    }
}

// Mock for tests and previews
final class MockUserService: UserServiceProtocol {
    var stubbedUsers: [User] = User.previews
    var shouldThrow = false

    func fetchUsers() async throws -> [User] {
        if shouldThrow { throw AppError.networkUnavailable }
        return stubbedUsers
    }

    func deleteUser(id: UUID) async throws {
        stubbedUsers.removeAll { $0.id == id }
    }
}
```

- Every service has a protocol.
- ViewModels receive protocols, not concrete types.
- Mocks implement protocols for tests and SwiftUI previews.
- Use a simple DI container or factory for wiring:

```swift
@MainActor
final class DependencyContainer {
    static let shared = DependencyContainer()

    lazy var apiClient: APIClientProtocol = APIClient()
    lazy var userService: UserServiceProtocol = UserService(apiClient: apiClient)
    // ...
}
```

## KMP Integration

```swift
// Shared/KMP/{Module}Bridge.swift
import shared  // KMP framework

final class HabitRepositoryBridge: HabitRepositoryProtocol {
    private let kmpRepo: SharedHabitRepository

    init() {
        self.kmpRepo = SharedHabitRepository()
    }

    func getHabits() async throws -> [Habit] {
        try await kmpRepo.getHabits().map { Habit(from: $0) }
    }
}
```

- Wrap KMP shared code in a Swift bridge that conforms to a Swift protocol.
- Map KMP types to Swift domain models at the bridge boundary.
- Never expose KMP types directly to ViewModels or Views.
- Follow Link's integration guide for each KMP module.

## Accessibility (WCAG 2.1 AA)

```swift
// Every interactive element
Button(action: viewModel.save) {
    Label("Save Changes", systemImage: "checkmark")
}
.accessibilityLabel("Save Changes")
.accessibilityHint("Saves your profile updates")

// Custom components
UserRowView(user: user)
    .accessibilityElement(children: .combine)
    .accessibilityLabel("\(user.name), \(user.role)")
    .accessibilityAddTraits(.isButton)

// Images
Image("profile")
    .accessibilityLabel("Profile photo of \(user.name)")

// Decorative images
Image("background-pattern")
    .accessibilityHidden(true)
```

Rules:
- **VoiceOver label** on every interactive element. Test with VoiceOver on device.
- **Dynamic Type**: Use system fonts (`.body`, `.headline`, etc.) or scaled custom fonts. Never hardcode font sizes.
- **Touch targets**: Minimum 44×44 pt. Use `.contentShape(Rectangle())` on custom hit areas.
- **Color contrast**: 4.5:1 for normal text, 3:1 for large text. Never convey information by color alone.
- **Semantic grouping**: `.accessibilityElement(children: .combine)` for logically grouped content.
- **Announcements**: `UIAccessibility.post(notification: .announcement, argument: "Item deleted")` for dynamic changes.
- **Reduce Motion**: Respect `@Environment(\.accessibilityReduceMotion)` for animations.

## Design System Integration

```swift
// DesignSystem/Tokens/Colors.swift
extension Color {
    static let appPrimary = Color("Primary", bundle: .main)      // from Asset catalog
    static let appBackground = Color("Background", bundle: .main)
    static let appTextPrimary = Color("TextPrimary", bundle: .main)
}

// DesignSystem/Tokens/Typography.swift
extension Font {
    static let appTitle = Font.system(.title, design: .default, weight: .bold)
    static let appBody = Font.system(.body, design: .default)
    static let appCaption = Font.system(.caption, design: .default)
}

// DesignSystem/Tokens/Spacing.swift
enum Spacing {
    static let xxs: CGFloat = 4
    static let xs: CGFloat = 8
    static let sm: CGFloat = 12
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
}
```

- Pixel's design tokens are the single source of truth.
- Colors in Asset Catalog for automatic dark mode support.
- No hardcoded colors, font sizes, or spacing in views.
- System fonts for Dynamic Type support.

## Testing

### Test Types & Framework Stack

| Test Type | Framework | Location | Run By |
|-----------|-----------|----------|--------|
| Unit (ViewModel, Service) | XCTest + MockK/Protocol mocks | `Tests/{Feature}Tests/` | CI (every commit) |
| Integration (API + DB) | XCTest + URLProtocol mock | `Tests/IntegrationTests/` | CI (every PR) |
| UI (SwiftUI views) | XCUITest | `UITests/` | CI (every PR) |
| Screenshot / Visual Regression | swift-snapshot-testing | `Tests/SnapshotTests/` | CI (every PR) |
| E2E (user flows) | XCUITest | `UITests/E2E/` | CI (nightly) |
| Performance Benchmarking | XCTest `measure(metrics:)` | `Tests/PerformanceTests/` | CI (nightly) |
| Security | Xcode Analyze + dependency audit | Build settings | CI (every PR) |
| Accessibility | XCTest accessibility assertions + VoiceOver | `Tests/` + manual | CI (every PR) + manual |

> **Full reference with code examples:** See @docs/references/swiftui-testing-reference.md

### Testing Rules Summary

- Unit test every ViewModel method. Mock services via protocols.
- `@MainActor` on test classes that test ViewModels.
- UI tests for critical user flows (auth, main feature, error states).
- Screenshot tests for every design system component and screen states (light/dark/Dynamic Type).
- E2E tests for end-to-end user flows (nightly).
- Performance benchmarks track startup, scroll, and ViewModel load time.
- Security tests validate Keychain, certificate pinning, ATS, and log sanitization.
- Accessibility tests validate labels, touch targets, Dynamic Type, and screen reader compatibility.
- Coverage: 80%+ ViewModels, 60%+ overall.
- Use `--ui-testing` launch argument to configure mock backends in UI tests.
- **Given / When / Then** structure in all tests (or arrange/act/assert).

## Performance

| Metric | Target |
|--------|--------|
| Render frame rate | 60 fps |
| Response to interaction | < 100ms |
| App launch (warm) | < 1s |
| Memory (idle screen) | < 50MB |

Rules:
- `LazyVStack` / `LazyHStack` for long lists — never `VStack` with 50+ items.
- `@StateObject` for owned objects, `@ObservedObject` for passed-in objects. Never `@StateObject` on a parent-created object.
- Avoid expensive computation in `body` — use `.task {}` or precompute in ViewModel.
- Images: use system caching (`URLCache`), resize before display, use `.resizable()` + `.aspectRatio()`.
- Profile with Instruments (Time Profiler, Allocations) before optimizing.

## Security in Code

- Sensitive data (tokens, passwords): Keychain only. Never `UserDefaults`.
- Certificate pinning for API calls in production.
- No logging of sensitive data (tokens, PII).
- Biometric auth (`LAContext`) for sensitive operations.
- App Transport Security: HTTPS only, no exceptions in production.
- Clear sensitive data from memory on backgrounding (`scenePhase` observer).

## Observability

### Structured Logging

- Use the KMP `Logger` actual for shared code; for iOS-only code use `os.Logger` or the project's chosen logging framework.
- Log categories: one `Logger` per subsystem/module (e.g., `Logger(subsystem: Bundle.main.bundleIdentifier!, category: "Networking")`).
- Log levels: fault (crash-worthy), error (unexpected), warning (recoverable), info (state change), debug (verbose, off in release).
- Use string interpolation with privacy: `logger.info("User loaded: \(userId, privacy: .public)")` — default to `.private` for any data that could be PII.
- Never log tokens, passwords, PII in plain text.

### Crash Reporting

- Integrate via KMP `CrashReporter` actual in `iosMain`.
- Configure: user ID binding on login, custom keys for screen/state context.
- Breadcrumbs: log navigation events (SwiftUI `.onAppear`/`.onDisappear`), network calls, user actions.
- dSYM upload: automate via build phase script or CI — without dSYMs, crash reports are useless.
- Non-fatal exceptions: report caught errors that indicate unexpected state via `CrashReporter.logException()`.
- Memory warnings: log `UIApplication.didReceiveMemoryWarningNotification` as breadcrumbs.

### Performance Monitoring

- Use the KMP `PerformanceTrace` actual in `iosMain`.
- Auto-instrument: app launch time, screen load time, network calls.
- Custom traces: wrap critical user flows (checkout, search, media loading) with `performance.mark()`/`performance.measure()`.
- Hang detection: monitor main thread hangs > 250ms — log with stack trace context.
- MetricKit integration: subscribe to `MXMetricManager` for Apple-provided diagnostics (hang rate, disk writes, CPU time, launch time) — forward to your metrics backend.
- Memory monitoring: track footprint via `os_proc_available_memory()`, report high-water marks.

### App Lifecycle Observability

- Track: `scenePhase` transitions (active/inactive/background), first meaningful paint, time-to-interactive per screen.
- Session tracking: generate a session ID on app launch, attach to all logs and traces.
- Deep link / push notification attribution: log the source that triggered each app open.
- Widget/extension usage: if the app has extensions, track their activations separately.

### Alerting Thresholds

- Crash-free rate: alert if < 99.5%
- Hang rate: alert if > 1% of sessions
- Launch time P95: alert if > 3s
- Network error rate: alert if > 2%

> **Full reference with code examples:** See @docs/references/swiftui-observability-reference.md

### Key Rules

- All observability goes through KMP shared interfaces — iOS module provides `actual` implementations.
- Inject via the DI container — never hardcode a specific vendor SDK.
- Reference `@.claude/rules/mobile/shared/kmp-coding-standards.md` for shared observability interfaces.
- Reference `@.claude/rules/shared/operational-standards.md` for SLO/alerting baselines.

## Concurrency

```swift
// Structured concurrency — prefer over unstructured Task {}
func loadDashboard() async {
    async let users = userService.fetchUsers()
    async let stats = analyticsService.fetchStats()

    do {
        let (fetchedUsers, fetchedStats) = try await (users, stats)
        state = .loaded(fetchedUsers, fetchedStats)
    } catch {
        state = .error(.unexpected(error))
    }
}

// Task cancellation
func search(query: String) {
    searchTask?.cancel()
    searchTask = Task {
        try await Task.sleep(for: .milliseconds(300)) // debounce
        guard !Task.isCancelled else { return }
        let results = try await searchService.search(query)
        guard !Task.isCancelled else { return }
        state = .loaded(results)
    }
}
```

- `async let` for parallel independent calls.
- Check `Task.isCancelled` after async boundaries.
- Cancel previous tasks when starting new ones (search, pagination).
- `@MainActor` for all UI-bound code. Use `nonisolated` for pure computation helpers.
