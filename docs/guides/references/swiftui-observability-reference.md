# SwiftUI Observability Reference

This is the detailed observability reference with code examples for SwiftUI/iOS. See `.claude/rules/mobile/ios/swiftui-coding-standards.md` for the summary rules.

## Structured Logging

```swift
// Core/Logging/LoggerExtension.swift
import os.Log

extension Logger {
    static let networking = Logger(subsystem: Bundle.main.bundleIdentifier ?? "", category: "Networking")
    static let persistence = Logger(subsystem: Bundle.main.bundleIdentifier ?? "", category: "Persistence")
    static let viewModel = Logger(subsystem: Bundle.main.bundleIdentifier ?? "", category: "ViewModel")
}

// Usage in service
Logger.networking.info("Request: \(url, privacy: .public), status: \(statusCode)")
Logger.viewModel.error("Failed to load: \(error.localizedDescription, privacy: .public)")
```

## Crash Reporting

```swift
// Core/CrashReporting/CrashReporterBridge.swift
import shared

/// Thin bridge over the shared `CrashReporter` interface. Every method here
/// maps to a member that actually exists on the KMP interface — see
/// `kmp-observability-reference.md` § Crash Reporting. If you need a method
/// that is not there, add it to the shared interface first; do not invent a
/// name on the Swift side, because nothing will fail until runtime.
final class CrashReporterBridge {
    static let shared = CrashReporterBridge()
    // Top-level Kotlin functions are exported under a class named after their
    // FILE: `getCrashReporter()` lives in `CrashReporter.kt`, so Swift sees
    // `CrashReporterKt`. Move the function to another file and this name
    // changes with it.
    private let kmpReporter: CrashReporter = CrashReporterKt.getCrashReporter()

    func setUserId(_ userId: String) {
        kmpReporter.setUserId(userId: userId)
    }

    func setCustomKey(_ key: String, value: String) {
        kmpReporter.setCustomKey(key: key, value: value)
    }

    func clearCustomKeys() {
        kmpReporter.clearCustomKeys()
    }

    func addBreadcrumb(message: String, level: BreadcrumbLevel = .info) {
        kmpReporter.addBreadcrumb(message: message, level: level)
    }

    /// Named `logException` to match the shared interface — NOT
    /// `recordException`, which does not exist on it.
    ///
    /// A Swift `Error` is not a `KotlinThrowable`, so it has to be wrapped.
    /// Use `String(describing:)`, which preserves the domain and code, rather
    /// than `localizedDescription`, which flattens every NSError to the same
    /// user-facing sentence and makes crashes impossible to group.
    func logException(_ error: Error, context: [String: String] = [:]) {
        let description = String(describing: error)
        kmpReporter.logException(
            throwable: KotlinThrowable(message: description),
            context: context
        )
    }
}

// Usage
struct UserProfileScreen: View {
    @StateObject private var viewModel: UserProfileViewModel

    var body: some View {
        content
            .onAppear {
                CrashReporterBridge.shared.addBreadcrumb(message: "UserProfileScreen appeared")
            }
            .onDisappear {
                CrashReporterBridge.shared.addBreadcrumb(message: "UserProfileScreen disappeared")
            }
    }
}
```

## Performance Monitoring

```swift
// Core/Performance/PerformanceTracker.swift
import os.Signpost

final class PerformanceTracker {
    static let shared = PerformanceTracker()
    private let signpostLog = OSLog(subsystem: Bundle.main.bundleIdentifier ?? "", category: .pointsOfInterest)

    func measure<T>(_ name: String, block: @escaping () async -> T) async -> T {
        let signpostID = OSSignpostID(log: signpostLog)
        os_signpost(.begin, log: signpostLog, name: "Loading", signpostID: signpostID)
        let result = await block()
        os_signpost(.end, log: signpostLog, name: "Loading", signpostID: signpostID)
        return result
    }
}

// Usage — `state` is an enum, so match on the case. There is no
// `state.isLoading` property; the four states are branches, not flags.
var body: some View {
    ZStack {
        if case .loading = viewModel.state {
            ProgressView()
                .task {
                    await PerformanceTracker.shared.measure("UserProfileLoad") {
                        await viewModel.loadProfile()
                    }
                }
        }
    }
}
```

## App Lifecycle Observability

```swift
// App/AppDelegate.swift
// `@main`, not the deprecated `@UIApplicationMain`.
// In a SwiftUI app the entry point is the App struct, which adopts this
// delegate via @UIApplicationDelegateAdaptor — see below.
final class AppDelegate: NSObject, UIApplicationDelegate {
    private let sessionId = UUID().uuidString

    // The parameter needs an INTERNAL name (`launchOptions`) as well as the
    // external one. Declared as `didFinishLaunchingWithOptions:` alone, the
    // value is unnamed inside the body and every `launchOptions` below fails
    // to compile.
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        let launchSource: String
        // The payload is unused — bind with `_` rather than an unused `let`.
        if launchOptions?[.remoteNotification] != nil {
            launchSource = "push_notification"
        } else if let url = launchOptions?[.url] as? URL {
            launchSource = "deep_link: \(url.scheme ?? "unknown")"
        } else {
            launchSource = "direct"
        }

        CrashReporterBridge.shared.addBreadcrumb(message: "App launched: \(launchSource)")
        Logger.viewModel.info(
            "Session started: \(self.sessionId, privacy: .public), source: \(launchSource, privacy: .public)"
        )

        return true
    }
}

// App/{App}App.swift
@main
struct MyApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup { RootScreen() }
    }
}
```
