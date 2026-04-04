import Foundation

// MARK: - APIError

enum APIError: Error, LocalizedError {
    case notConfigured                         // remote mode off or URL invalid
    case invalidURL(String)
    case encodingFailed(Error)
    case networkError(Error)
    case httpError(statusCode: Int, body: String)
    case decodingFailed(Error)

    var errorDescription: String? {
        switch self {
        case .notConfigured:
            return "Remote backend is not configured. Enable it in App Settings."
        case .invalidURL(let url):
            return "Invalid backend URL: \(url)"
        case .encodingFailed(let e):
            return "Failed to encode request: \(e.localizedDescription)"
        case .networkError(let e):
            return "Network error: \(e.localizedDescription)"
        case .httpError(let code, let body):
            return "Server error \(code): \(body)"
        case .decodingFailed(let e):
            return "Failed to decode response: \(e.localizedDescription)"
        }
    }
}

// MARK: - APIClient
// Generic, reusable HTTP client. No renovation-domain knowledge.
// All methods are async throws and run on @MainActor callers.

final class APIClient {
    let baseURL: URL

    private let session: URLSession
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session

        encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601

        decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
    }

    // GET — decodes response body into T
    func get<T: Decodable>(_ path: String) async throws -> T {
        let req = try makeRequest(path: path, method: "GET", body: Optional<EmptyBody>.none)
        return try await perform(req)
    }

    // POST — encodes body, decodes response
    func post<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        let req = try makeRequest(path: path, method: "POST", body: body)
        return try await perform(req)
    }

    // PUT — encodes body, decodes response
    func put<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        let req = try makeRequest(path: path, method: "PUT", body: body)
        return try await perform(req)
    }

    // DELETE — no response body
    func delete(_ path: String) async throws {
        let req = try makeRequest(path: path, method: "DELETE", body: Optional<EmptyBody>.none)
        let (_, response) = try await session.data(for: req)
        try validateStatus(response)
    }

    // MARK: - Private helpers

    private func makeRequest<B: Encodable>(
        path: String,
        method: String,
        body: B?
    ) throws -> URLRequest {
        guard let url = URL(string: path, relativeTo: baseURL) else {
            throw APIError.invalidURL("\(baseURL)\(path)")
        }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            do { req.httpBody = try encoder.encode(body) }
            catch { throw APIError.encodingFailed(error) }
        }
        return req
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.networkError(error)
        }
        try validateStatus(response, data: data)
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingFailed(error)
        }
    }

    private func validateStatus(_ response: URLResponse, data: Data = Data()) throws {
        guard let http = response as? HTTPURLResponse else { return }
        guard (200..<300).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw APIError.httpError(statusCode: http.statusCode, body: body)
        }
    }
}

// Sentinel type so generic methods compile with a nil body
private struct EmptyBody: Encodable {}

// MARK: - DTOs
// These must exactly mirror the JSON field names from the Go backend (dto.go).
// They are SEPARATE from the @Model classes — never conflate them.

struct ProjectDTO: Codable, Identifiable {
    let id: String
    var name: String
    var address: String
    var totalBudget: Double
    var startDate: String   // ISO8601 RFC3339
    var targetDate: String
    var status: String

    enum CodingKeys: String, CodingKey {
        case id, name, address, status
        case totalBudget = "total_budget"
        case startDate   = "start_date"
        case targetDate  = "target_date"
    }
}

struct RoomDTO: Codable, Identifiable {
    let id: String
    let projectId: String
    var name: String
    var areaSqm: Double

    enum CodingKeys: String, CodingKey {
        case id, name
        case projectId = "project_id"
        case areaSqm   = "area_sqm"
    }
}

struct TaskDTO: Codable, Identifiable {
    let id: String
    let roomId: String
    var name: String
    var category: String
    var status: String
    var estimatedCost: Double
    var actualCost: Double?
    var contractor: String
    var notes: String
    var dueDate: String?

    enum CodingKeys: String, CodingKey {
        case id, name, category, status, contractor, notes
        case roomId        = "room_id"
        case estimatedCost = "estimated_cost"
        case actualCost    = "actual_cost"
        case dueDate       = "due_date"
    }
}

// Request bodies (no server-assigned fields)

struct CreateProjectBody: Encodable {
    var name: String
    var address: String
    var totalBudget: Double
    var startDate: String
    var targetDate: String
    var status: String

    enum CodingKeys: String, CodingKey {
        case name, address, status
        case totalBudget = "total_budget"
        case startDate   = "start_date"
        case targetDate  = "target_date"
    }
}

struct CreateRoomBody: Encodable {
    var name: String
    var areaSqm: Double

    enum CodingKeys: String, CodingKey {
        case name
        case areaSqm = "area_sqm"
    }
}

struct CreateTaskBody: Encodable {
    var name: String
    var category: String
    var status: String
    var estimatedCost: Double
    var actualCost: Double?
    var contractor: String
    var notes: String
    var dueDate: String?

    enum CodingKeys: String, CodingKey {
        case name, category, status, contractor, notes
        case estimatedCost = "estimated_cost"
        case actualCost    = "actual_cost"
        case dueDate       = "due_date"
    }
}

// MARK: - RenovationAPIService
// Typed facade over APIClient for all renovation-domain endpoints.

@MainActor
final class RenovationAPIService {
    private let client: APIClient

    init(settings: AppSettings) {
        // Falls back to localhost if URL is misconfigured — real errors surface
        // at the network call level as APIError.httpError.
        let base = settings.resolvedBaseURL ?? URL(string: "http://localhost:8777")!
        client = APIClient(baseURL: base)
    }

    // MARK: Projects

    func fetchProjects() async throws -> [ProjectDTO] {
        try await client.get("/api/v1/projects")
    }

    func fetchProject(id: String) async throws -> ProjectDTO {
        try await client.get("/api/v1/projects/\(id)")
    }

    func createProject(_ body: CreateProjectBody) async throws -> ProjectDTO {
        try await client.post("/api/v1/projects", body: body)
    }

    func updateProject(id: String, _ body: CreateProjectBody) async throws -> ProjectDTO {
        try await client.put("/api/v1/projects/\(id)", body: body)
    }

    func deleteProject(id: String) async throws {
        try await client.delete("/api/v1/projects/\(id)")
    }

    // MARK: Rooms

    func fetchRooms(projectId: String) async throws -> [RoomDTO] {
        try await client.get("/api/v1/projects/\(projectId)/rooms")
    }

    func createRoom(projectId: String, _ body: CreateRoomBody) async throws -> RoomDTO {
        try await client.post("/api/v1/projects/\(projectId)/rooms", body: body)
    }

    func updateRoom(id: String, _ body: CreateRoomBody) async throws -> RoomDTO {
        try await client.put("/api/v1/rooms/\(id)", body: body)
    }

    func deleteRoom(id: String) async throws {
        try await client.delete("/api/v1/rooms/\(id)")
    }

    // MARK: Tasks

    func fetchTasks(roomId: String) async throws -> [TaskDTO] {
        try await client.get("/api/v1/rooms/\(roomId)/tasks")
    }

    func createTask(roomId: String, _ body: CreateTaskBody) async throws -> TaskDTO {
        try await client.post("/api/v1/rooms/\(roomId)/tasks", body: body)
    }

    func updateTask(id: String, _ body: CreateTaskBody) async throws -> TaskDTO {
        try await client.put("/api/v1/tasks/\(id)", body: body)
    }

    func deleteTask(id: String) async throws {
        try await client.delete("/api/v1/tasks/\(id)")
    }

    // MARK: Health

    func checkHealth() async throws {
        struct HealthResponse: Decodable { let status: String }
        let _: HealthResponse = try await client.get("/health")
    }
}

// MARK: - Date helpers for DTO conversion

extension Date {
    /// Formats a Date as an ISO8601 RFC3339 string for sending to the Go backend.
    var rfc3339: String {
        ISO8601DateFormatter().string(from: self)
    }
}

extension String {
    /// Parses an RFC3339 string back to a Date. Returns nil if parsing fails.
    var asDate: Date? {
        ISO8601DateFormatter().date(from: self)
    }
}
