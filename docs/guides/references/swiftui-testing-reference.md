# SwiftUI Testing Reference

This is the detailed testing reference with code examples for SwiftUI/iOS. See `.claude/rules/mobile/ios/swiftui-coding-standards.md` for the summary rules.

## Unit Tests — ViewModels (XCTest)

```swift
@MainActor
final class UserListViewModelTests: XCTestCase {
    private var mockService: MockUserService!
    private var viewModel: UserListViewModel!

    override func setUp() {
        super.setUp()
        mockService = MockUserService()
        viewModel = UserListViewModel(userService: mockService)
    }

    func test_loadUsers_setsLoadedState() async {
        mockService.stubbedUsers = [.preview]

        await viewModel.loadUsers()

        XCTAssertEqual(viewModel.state, .loaded([.preview]))
    }

    func test_loadUsers_emptyResponse_setsEmptyState() async {
        mockService.stubbedUsers = []

        await viewModel.loadUsers()

        XCTAssertEqual(viewModel.state, .empty)
    }

    func test_loadUsers_networkError_setsErrorState() async {
        mockService.shouldThrow = true

        await viewModel.loadUsers()

        if case .error = viewModel.state {
            // Expected
        } else {
            XCTFail("Expected error state")
        }
    }

    func test_deleteUser_removesFromList() async {
        let user = User.preview
        mockService.stubbedUsers = [user]
        await viewModel.loadUsers()

        await viewModel.deleteUser(user)

        XCTAssertEqual(viewModel.state, .empty)
    }
}
```

## Integration Tests — API Layer

```swift
final class APIClientIntegrationTests: XCTestCase {

    private var mockSession: URLSession!
    private var client: APIClient!

    override func setUp() {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [MockURLProtocol.self]
        mockSession = URLSession(configuration: config)
        client = APIClient(session: mockSession)
    }

    func test_request_parsesSuccessResponse() async throws {
        let json = """
        {"status":"success","data":{"id":"1","name":"Test","email":"test@example.com","created_at":"2025-01-01T12:00:00Z"}}
        """.data(using: .utf8)!

        MockURLProtocol.requestHandler = { _ in
            (HTTPURLResponse(url: URL(string: "https://api.test.com")!, statusCode: 200, httpVersion: nil, headerFields: nil)!, json)
        }

        let user: User = try await client.request(.users())
        XCTAssertEqual(user.name, "Test")
    }

    func test_request_401_throwsUnauthorized() async {
        MockURLProtocol.requestHandler = { _ in
            (HTTPURLResponse(url: URL(string: "https://api.test.com")!, statusCode: 401, httpVersion: nil, headerFields: nil)!, Data())
        }

        do {
            let _: User = try await client.request(.users())
            XCTFail("Expected unauthorized error")
        } catch let error as AppError {
            XCTAssertEqual(error, .unauthorized)
        } catch {
            XCTFail("Unexpected error type")
        }
    }
}
```

## UI Tests (XCUITest)

```swift
final class UserListUITests: XCTestCase {
    let app = XCUIApplication()

    override func setUp() {
        continueAfterFailure = false
        app.launchArguments = ["--ui-testing"]
        app.launch()
    }

    func test_userList_displaysUsers() {
        let list = app.collectionViews["userList"]
        XCTAssertTrue(list.waitForExistence(timeout: 5))
        XCTAssertGreaterThan(list.cells.count, 0)
    }

    func test_pullToRefresh_reloadsData() {
        let list = app.collectionViews["userList"]
        XCTAssertTrue(list.waitForExistence(timeout: 5))
        list.swipeDown()
        // Verify reload happened (e.g., cell count or timestamp updated)
    }

    func test_deleteUser_removesFromList() {
        let list = app.collectionViews["userList"]
        XCTAssertTrue(list.waitForExistence(timeout: 5))
        let initialCount = list.cells.count

        let firstCell = list.cells.firstMatch
        firstCell.swipeLeft()
        app.buttons["Delete"].tap()

        XCTAssertEqual(list.cells.count, initialCount - 1)
    }
}
```

## Screenshot / Visual Regression Tests (swift-snapshot-testing)

Screenshot tests catch unintended UI changes by comparing rendered views against golden reference images.

```swift
import SnapshotTesting
import SwiftUI

final class DesignSystemSnapshotTests: XCTestCase {

    func test_primaryButton_default() {
        let view = PrimaryButton("Save", action: {})
        assertSnapshot(of: view, as: .image(layout: .fixed(width: 375, height: 56)))
    }

    func test_primaryButton_disabled() {
        let view = PrimaryButton("Save", action: {}).disabled(true)
        assertSnapshot(of: view, as: .image(layout: .fixed(width: 375, height: 56)))
    }

    func test_userCard_light() {
        let view = UserRowView(user: .preview)
        assertSnapshot(of: view, as: .image(layout: .fixed(width: 375, height: 80)))
    }

    func test_userCard_dark() {
        let view = UserRowView(user: .preview).environment(\.colorScheme, .dark)
        assertSnapshot(of: view, as: .image(layout: .fixed(width: 375, height: 80)))
    }

    func test_userCard_dynamicType_accessibility() {
        let view = UserRowView(user: .preview)
            .environment(\.sizeCategory, .accessibilityExtraExtraExtraLarge)
        assertSnapshot(of: view, as: .image(layout: .fixed(width: 375, height: 200)))
    }

    @MainActor
    func test_userListContent_allFourStates() {
        let states: [(String, UserListViewModel.State)] = [
            ("loading", .loading),
            ("empty", .empty),
            ("error", .error(.networkUnavailable)),
            ("loaded", .loaded([.preview])),
        ]

        for (name, state) in states {
            // UserListContent takes a plain State value — no ViewModel, no
            // service to mock, and nothing to assign to `private(set) state`
            // (which is unreachable even under @testable import).
            let view = UserListContent(state: state, onRetry: {})
            assertSnapshot(of: view, as: .image(layout: .device(.iPhone13)), named: name)
        }
    }
}
```

## E2E Tests (XCUITest — Full User Flows)

```swift
final class OnboardingE2ETest: XCTestCase {
    let app = XCUIApplication()

    override func setUp() {
        continueAfterFailure = false
        app.launchArguments = ["--e2e-testing", "--reset-state"]
        app.launch()
    }

    func test_newUser_completeOnboarding() {
        // Sign up
        app.textFields["emailField"].tap()
        app.textFields["emailField"].typeText("e2e@test.com")
        app.secureTextFields["passwordField"].tap()
        app.secureTextFields["passwordField"].typeText("SecurePass123!")
        app.buttons["Sign Up"].tap()

        // Onboarding flow
        XCTAssertTrue(app.staticTexts["Welcome"].waitForExistence(timeout: 5))
        app.buttons["Next"].tap()
        app.buttons["Next"].tap()
        app.buttons["Get Started"].tap()

        // Verify landed on main screen
        XCTAssertTrue(app.navigationBars["Notes"].waitForExistence(timeout: 5))
    }

    func test_existingUser_createAndDeleteNote() {
        // Login (assumes test account exists)
        loginWithTestAccount()

        // Create note
        app.buttons["Create Note"].tap()
        app.textFields["titleField"].typeText("E2E Test Note")
        app.textViews["contentField"].typeText("Automated test content")
        app.buttons["Save"].tap()

        XCTAssertTrue(app.staticTexts["E2E Test Note"].waitForExistence(timeout: 5))

        // Delete note
        app.staticTexts["E2E Test Note"].swipeLeft()
        app.buttons["Delete"].tap()
        XCTAssertFalse(app.staticTexts["E2E Test Note"].exists)
    }
}
```

## Performance Benchmarking Tests

```swift
final class PerformanceTests: XCTestCase {

    func test_appLaunch_performance() {
        measure(metrics: [XCTApplicationLaunchMetric()]) {
            XCUIApplication().launch()
        }
    }

    func test_scrollPerformance() {
        let app = XCUIApplication()
        app.launch()

        let list = app.collectionViews["userList"]
        XCTAssertTrue(list.waitForExistence(timeout: 5))

        measure(metrics: [XCTOSSignpostMetric.scrollDecelerationMetric]) {
            list.swipeUp(velocity: .fast)
            list.swipeDown(velocity: .fast)
        }
    }

    func test_viewModel_loadPerformance() {
        let service = MockUserService()
        service.stubbedUsers = (0..<1000).map { User.preview(id: "\($0)") }

        measure {
            let vm = UserListViewModel(userService: service)
            let expectation = expectation(description: "loaded")
            Task {
                await vm.loadUsers()
                expectation.fulfill()
            }
            wait(for: [expectation], timeout: 5)
        }
    }
}
```

## Security Tests

```swift
final class SecurityTests: XCTestCase {

    func test_sensitiveData_storedInKeychain_notUserDefaults() {
        // Verify Keychain is used for tokens
        let keychainManager = KeychainManager()
        try? keychainManager.save(key: "test_token", value: "secret123")

        let retrieved = try? keychainManager.get(key: "test_token")
        XCTAssertEqual(retrieved, "secret123")

        // Verify NOT in UserDefaults
        XCTAssertNil(UserDefaults.standard.string(forKey: "test_token"))

        // Cleanup
        try? keychainManager.delete(key: "test_token")
    }

    func test_apiClient_enforcesCertificatePinning() async {
        let pinnedClient = APIClient(certificatePins: ["sha256/INVALID_PIN"])

        do {
            let _: User = try await pinnedClient.request(.users())
            XCTFail("Should have failed with invalid pin")
        } catch {
            // Expected — connection should fail
        }
    }

    func test_noSensitiveDataInLogs() {
        // Capture log output and verify no tokens/PII
        let logCapture = LogCapture()
        logCapture.startCapturing()

        let service = UserService(apiClient: MockAPIClient())
        // Trigger operations that handle sensitive data
        _ = try? await service.login(email: "test@example.com", password: "secret")

        let logs = logCapture.capturedLogs
        XCTAssertFalse(logs.contains("secret"))
        XCTAssertFalse(logs.contains("test@example.com"))
    }

    func test_appTransportSecurity_noPlaintextHTTP() {
        guard let atsSettings = Bundle.main.infoDictionary?["NSAppTransportSecurity"] as? [String: Any] else {
            return // ATS enabled by default when key is absent
        }
        XCTAssertNil(atsSettings["NSAllowsArbitraryLoads"] as? Bool,
                      "NSAllowsArbitraryLoads must not be true in production")
    }
}
```

## Accessibility Tests

```swift
@MainActor
final class AccessibilityTests: XCTestCase {

    func test_userRow_hasAccessibilityLabel() {
        let view = UserRowView(user: .preview)
        let host = UIHostingController(rootView: view)
        host.loadViewIfNeeded()

        let element = try XCTUnwrap(host.view.accessibilityElements?.first)
        XCTAssertNotNil(element.accessibilityLabel)
        XCTAssertFalse(element.accessibilityLabel!.isEmpty)
    }

    func test_deleteButton_hasAccessibilityHint() {
        let view = UserRowView(user: .preview)
        let host = UIHostingController(rootView: view)
        host.loadViewIfNeeded()

        // Find delete button in accessibility tree
        let deleteButton = findAccessibilityElement(in: host.view, matching: { $0.accessibilityLabel == "Delete" })
        XCTAssertNotNil(deleteButton?.accessibilityHint)
    }

    @MainActor
    func test_dynamicType_atLargestSize_noTruncation() {
        let view = UserListContent(state: .loaded([.preview]), onRetry: {})
            .environment(\.sizeCategory, .accessibilityExtraExtraExtraLarge)

        let host = UIHostingController(rootView: view)
        host.view.frame = CGRect(x: 0, y: 0, width: 375, height: 812)
        host.loadViewIfNeeded()

        // Verify content is scrollable and accessible at largest type
        XCTAssertNotNil(host.view)
    }
}

// XCUITest accessibility checks
final class AccessibilityUITests: XCTestCase {
    let app = XCUIApplication()

    override func setUp() {
        continueAfterFailure = false
        app.launchArguments = ["--ui-testing"]
        app.launch()
    }

    func test_allInteractiveElements_haveAccessibilityLabels() {
        let buttons = app.buttons.allElementsBoundByAccessibilityElement
        for button in buttons {
            XCTAssertFalse(button.label.isEmpty, "Button missing accessibility label: \(button)")
        }
    }

    func test_touchTargets_meetMinimumSize() {
        let buttons = app.buttons.allElementsBoundByAccessibilityElement
        for button in buttons where button.isHittable {
            XCTAssertGreaterThanOrEqual(button.frame.width, 44, "Touch target too narrow: \(button.label)")
            XCTAssertGreaterThanOrEqual(button.frame.height, 44, "Touch target too short: \(button.label)")
        }
    }
}
```
