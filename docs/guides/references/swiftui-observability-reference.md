# SwiftUI Observability Reference

This is the detailed observability reference with code examples for SwiftUI/iOS. See `.claude/rules/swiftui-coding-standards.md` for the summary rules.

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

final class CrashReporterBridge {
    static let shared = CrashReporterBridge()
    private let kmpReporter = SharedCrashReporter()

    func setUserId(_ userId: String) {
        kmpReporter.setUserId(userId)
    }

    func addBreadcrumb(message: String, level: String = "info") {
        kmpReporter.addBreadcrumb(message: message, level: level)
    }

    func recordException(_ error: Error) {
        kmpReporter.recordException(error.localizedDescription)
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

// Usage
var body: some View {
    ZStack {
        if viewModel.state.isLoading {
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
@UIApplicationMain
final class AppDelegate: UIResponder, UIApplicationDelegate {
    private let sessionId = UUID().uuidString

    func application(_ application: UIApplication, didFinishLaunchingWithOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        let launchSource: String
        if let notification = launchOptions?[.remoteNotification] {
            launchSource = "push_notification"
        } else if let url = launchOptions?[.url] as? URL {
            launchSource = "deep_link: \(url.scheme ?? "unknown")"
        } else {
            launchSource = "direct"
        }

        CrashReporterBridge.shared.addBreadcrumb(message: "App launched: \(launchSource)")
        Logger.viewModel.info("Session started: \(self.sessionId, privacy: .public), source: \(launchSource, privacy: .public)")

        return true
    }
}
```
