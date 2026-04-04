import Combine
import Foundation

// MARK: - AppSettings
// Single source of truth for the data-source mode.
// Backed by UserDefaults via @AppStorage so settings survive app restarts.
// Published properties drive SwiftUI updates throughout the app.

final class AppSettings: ObservableObject {

    // MARK: Singleton
    static let shared = AppSettings()

    // MARK: Persisted settings

    @Published var useRemoteBackend: Bool {
        didSet { UserDefaults.standard.set(useRemoteBackend, forKey: "useRemoteBackend") }
    }

    @Published var backendBaseURL: String {
        didSet { UserDefaults.standard.set(backendBaseURL, forKey: "backendBaseURL") }
    }

    // MARK: Init

    init() {
        // Load from UserDefaults on every init (handles first-launch defaults).
        self.useRemoteBackend = UserDefaults.standard.bool(forKey: "useRemoteBackend")
        let stored = UserDefaults.standard.string(forKey: "backendBaseURL") ?? ""
        self.backendBaseURL = stored.isEmpty ? "http://localhost:8777" : stored
    }

    // MARK: Derived

    /// Returns a valid URL for the backend, or nil if the string is malformed.
    var resolvedBaseURL: URL? {
        guard useRemoteBackend, let url = URL(string: backendBaseURL), url.scheme != nil else {
            return nil
        }
        return url
    }

    /// True only when remote mode is on AND the URL is structurally valid.
    var isRemoteReady: Bool { resolvedBaseURL != nil }
}
