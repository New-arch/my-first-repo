import SwiftUI
import SwiftData

// MARK: - NetworkSettingsView
// Appears as a sidebar item in ContentView, below the project list.
// Lets users toggle remote backend mode, configure the URL, test connectivity,
// and trigger a manual full sync.

struct NetworkSettingsView: View {
    @ObservedObject var settings: AppSettings
    @EnvironmentObject  var syncEngine: SyncEngine
    @Environment(\.modelContext) private var modelContext

    @State private var urlDraft: String = ""
    @State private var connectionStatus: ConnectionStatus = .idle

    enum ConnectionStatus {
        case idle, checking, ok, failed(String)

        var label: String {
            switch self {
            case .idle:          return ""
            case .checking:      return "Checking…"
            case .ok:            return "Connected"
            case .failed(let m): return m
            }
        }

        var color: Color {
            switch self {
            case .idle, .checking: return .secondary
            case .ok:              return .green
            case .failed:          return .red
            }
        }

        var icon: String? {
            switch self {
            case .ok:      return "checkmark.circle.fill"
            case .failed:  return "xmark.circle.fill"
            default:       return nil
            }
        }
    }

    var body: some View {
        Form {
            // ── Mode toggle ──────────────────────────────────
            Section {
                Toggle(isOn: $settings.useRemoteBackend) {
                    Label("Use Remote Backend", systemImage: "network")
                }
                .onChange(of: settings.useRemoteBackend) { _, enabled in
                    if enabled {
                        urlDraft = settings.backendBaseURL
                        connectionStatus = .idle
                    }
                }

                HStack {
                    Label("Mode", systemImage: settings.useRemoteBackend ? "cloud.fill" : "internaldrive.fill")
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(settings.useRemoteBackend ? "Remote + Local cache" : "Local only (SwiftData)")
                        .font(.footnote)
                        .foregroundStyle(settings.useRemoteBackend ? .blue : .green)
                }
            } header: {
                Text("Data Source")
            }

            // ── Backend URL (only shown in remote mode) ──────
            if settings.useRemoteBackend {
                Section {
                    TextField("http://…", text: $urlDraft)
                        .keyboardType(.URL)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                        .submitLabel(.done)
                        .onSubmit { applyURL() }
                        .onAppear { urlDraft = settings.backendBaseURL }

                    Button("Apply") { applyURL() }
                        .disabled(urlDraft == settings.backendBaseURL)
                } header: {
                    Text("Backend URL")
                } footer: {
                    Text("Default: http://localhost:8777  (Docker host port)")
                        .font(.caption)
                }

                // ── Connection test ──────────────────────────
                Section {
                    Button {
                        Task { await testConnection() }
                    } label: {
                        Label("Test Connection", systemImage: "antenna.radiowaves.left.and.right")
                    }

                    if connectionStatus.label.isEmpty == false {
                        HStack {
                            if case .checking = connectionStatus {
                                ProgressView().controlSize(.small)
                            } else if let icon = connectionStatus.icon {
                                Image(systemName: icon).foregroundStyle(connectionStatus.color)
                            }
                            Text(connectionStatus.label)
                                .font(.footnote)
                                .foregroundStyle(connectionStatus.color)
                        }
                    }
                }

                // ── Sync ─────────────────────────────────────
                Section {
                    Button {
                        Task { await syncEngine.syncAll(into: modelContext) }
                    } label: {
                        Label(
                            syncEngine.isSyncing ? "Syncing…" : "Sync Now",
                            systemImage: "arrow.triangle.2.circlepath"
                        )
                    }
                    .disabled(syncEngine.isSyncing || !settings.isRemoteReady)

                    if let date = syncEngine.lastSyncDate {
                        LabeledContent("Last Sync") {
                            Text(date, style: .relative)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                    }

                    if let error = syncEngine.lastError {
                        Label(error, systemImage: "exclamationmark.triangle.fill")
                            .font(.footnote)
                            .foregroundStyle(.red)
                            .lineLimit(3)
                    }
                } header: {
                    Text("Synchronisation")
                } footer: {
                    Text("Sync pulls all projects, rooms and tasks from the server into the local SwiftData cache. Subsequent edits push to both stores.")
                        .font(.caption)
                }
            }

            // ── About ─────────────────────────────────────────
            Section("About") {
                LabeledContent("API Base URL") {
                    Text(settings.backendBaseURL)
                        .font(.caption2.monospaced())
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
                LabeledContent("Swagger UI") {
                    Text("\(settings.backendBaseURL)/docs")
                        .font(.caption2.monospaced())
                        .foregroundStyle(.blue)
                        .lineLimit(2)
                }
            }
        }
        .navigationTitle("App Settings")
        .navigationBarTitleDisplayMode(.inline)
    }

    // MARK: - Actions

    private func applyURL() {
        settings.backendBaseURL = urlDraft
        connectionStatus = .idle
    }

    private func testConnection() async {
        connectionStatus = .checking
        do {
            let api = RenovationAPIService(settings: settings)
            try await api.checkHealth()
            connectionStatus = .ok
        } catch {
            let msg = (error as? APIError)?.errorDescription ?? error.localizedDescription
            connectionStatus = .failed(msg)
        }
    }
}
