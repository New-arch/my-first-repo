import Foundation
import SwiftData

// MARK: - SyncEngine
// Orchestrates all write operations that must touch both SwiftData (local cache)
// and the Go backend (remote). Reads always come from SwiftData via @Query.
//
// Usage pattern:
//   1. Caller creates/mutates the @Model object and inserts it into SwiftData.
//   2. Caller invokes the matching SyncEngine.push* method.
//   3. SyncEngine calls the REST API; on success it stamps remoteID on the object.
//   4. SwiftData auto-saves. All @Query views refresh automatically.
//
// When remote mode is OFF every push* method is a no-op — local behaviour is
// completely unchanged.

@MainActor
final class SyncEngine: ObservableObject {

    // MARK: Published state (observed by NetworkSettingsView)

    @Published var isSyncing = false
    @Published var lastError: String?
    @Published var lastSyncDate: Date?

    // MARK: Dependencies

    let settings: AppSettings
    private var api: RenovationAPIService? { settings.isRemoteReady ? RenovationAPIService(settings: settings) : nil }

    // MARK: Init

    init(settings: AppSettings = .shared) {
        self.settings = settings
    }

    // MARK: - Project operations

    /// Call after inserting a new RenovationProject into SwiftData.
    /// Stamps `project.remoteID` with the server-assigned UUID on success.
    func pushCreate(project: RenovationProject) async {
        guard let api else { return }
        let body = CreateProjectBody(
            name:        project.name,
            address:     project.address,
            totalBudget: project.totalBudget,
            startDate:   project.startDate.rfc3339,
            targetDate:  project.targetDate.rfc3339,
            status:      project.status
        )
        await run {
            let dto = try await api.createProject(body)
            project.remoteID = dto.id
        }
    }

    /// Call after mutating a project's fields in SwiftData.
    func pushUpdate(project: RenovationProject) async {
        guard let api, let remoteID = project.remoteID else { return }
        let body = CreateProjectBody(
            name:        project.name,
            address:     project.address,
            totalBudget: project.totalBudget,
            startDate:   project.startDate.rfc3339,
            targetDate:  project.targetDate.rfc3339,
            status:      project.status
        )
        await run { _ = try await api.updateProject(id: remoteID, body) }
    }

    /// Call BEFORE deleting a project from SwiftData (capture remoteID first).
    func pushDelete(projectRemoteID: String) async {
        guard let api else { return }
        await run { try await api.deleteProject(id: projectRemoteID) }
    }

    // MARK: - Room operations

    func pushCreate(room: Room, projectRemoteID: String) async {
        guard let api else { return }
        let body = CreateRoomBody(name: room.name, areaSqm: room.areaSqm)
        await run {
            let dto = try await api.createRoom(projectId: projectRemoteID, body)
            room.remoteID = dto.id
        }
    }

    func pushUpdate(room: Room) async {
        guard let api, let remoteID = room.remoteID else { return }
        let body = CreateRoomBody(name: room.name, areaSqm: room.areaSqm)
        await run { _ = try await api.updateRoom(id: remoteID, body) }
    }

    func pushDelete(roomRemoteID: String) async {
        guard let api else { return }
        await run { try await api.deleteRoom(id: roomRemoteID) }
    }

    // MARK: - Task operations

    func pushCreate(task: RenovationTask, roomRemoteID: String) async {
        guard let api else { return }
        let body = CreateTaskBody(
            name:          task.name,
            category:      task.category,
            status:        task.status,
            estimatedCost: task.estimatedCost,
            actualCost:    task.actualCost,
            contractor:    task.contractor,
            notes:         task.notes,
            dueDate:       task.dueDate?.rfc3339
        )
        await run {
            let dto = try await api.createTask(roomId: roomRemoteID, body)
            task.remoteID = dto.id
        }
    }

    func pushUpdate(task: RenovationTask) async {
        guard let api, let remoteID = task.remoteID else { return }
        let body = CreateTaskBody(
            name:          task.name,
            category:      task.category,
            status:        task.status,
            estimatedCost: task.estimatedCost,
            actualCost:    task.actualCost,
            contractor:    task.contractor,
            notes:         task.notes,
            dueDate:       task.dueDate?.rfc3339
        )
        await run { _ = try await api.updateTask(id: remoteID, body) }
    }

    func pushDelete(taskRemoteID: String) async {
        guard let api else { return }
        await run { try await api.deleteTask(id: taskRemoteID) }
    }

    // MARK: - Full sync (remote → SwiftData)
    // Fetches all projects (with rooms+tasks) from the server and upserts them
    // into SwiftData, matching on remoteID. Runs on the calling actor (MainActor).

    func syncAll(into context: ModelContext) async {
        guard let api else { return }
        isSyncing = true
        defer { isSyncing = false }

        await run {
            let projectDTOs: [ProjectDTO] = try await api.fetchProjects()

            // Build a lookup of existing SwiftData objects by remoteID
            var localProjects = try context.fetch(FetchDescriptor<RenovationProject>())
            let projectsByRemoteID = Dictionary(
                localProjects.compactMap { p in p.remoteID.map { ($0, p) } },
                uniquingKeysWith: { first, _ in first }
            )

            for dto in projectDTOs {
                let project: RenovationProject
                if let existing = projectsByRemoteID[dto.id] {
                    // Update existing local record
                    project = existing
                } else {
                    // Create new local record
                    project = RenovationProject(name: dto.name)
                    context.insert(project)
                }
                project.remoteID    = dto.id
                project.name        = dto.name
                project.address     = dto.address
                project.totalBudget = dto.totalBudget
                project.startDate   = dto.startDate.asDate ?? .now
                project.targetDate  = dto.targetDate.asDate ?? .now
                project.status      = dto.status

                // Sync rooms for this project
                let roomDTOs: [RoomDTO] = try await api.fetchRooms(projectId: dto.id)
                var localRooms = project.rooms
                let roomsByRemoteID = Dictionary(
                    localRooms.compactMap { r in r.remoteID.map { ($0, r) } },
                    uniquingKeysWith: { first, _ in first }
                )

                for rDto in roomDTOs {
                    let room: Room
                    if let existing = roomsByRemoteID[rDto.id] {
                        room = existing
                    } else {
                        room = Room(name: rDto.name)
                        context.insert(room)
                        project.rooms.append(room)
                    }
                    room.remoteID = rDto.id
                    room.name     = rDto.name
                    room.areaSqm  = rDto.areaSqm

                    // Sync tasks for this room
                    let taskDTOs: [TaskDTO] = try await api.fetchTasks(roomId: rDto.id)
                    let tasksByRemoteID = Dictionary(
                        room.tasks.compactMap { t in t.remoteID.map { ($0, t) } },
                        uniquingKeysWith: { first, _ in first }
                    )

                    for tDto in taskDTOs {
                        let task: RenovationTask
                        if let existing = tasksByRemoteID[tDto.id] {
                            task = existing
                        } else {
                            task = RenovationTask(name: tDto.name)
                            context.insert(task)
                            room.tasks.append(task)
                        }
                        task.remoteID      = tDto.id
                        task.name          = tDto.name
                        task.category      = tDto.category
                        task.status        = tDto.status
                        task.estimatedCost = tDto.estimatedCost
                        task.actualCost    = tDto.actualCost
                        task.contractor    = tDto.contractor
                        task.notes         = tDto.notes
                        task.dueDate       = tDto.dueDate?.asDate
                    }
                }
            }

            self.lastSyncDate = Date.now
        }
    }

    // MARK: - Private run helper
    // Wraps an async throwing block: catches errors into lastError.

    private func run(_ block: @escaping () async throws -> Void) async {
        do {
            try await block()
            lastError = nil
        } catch {
            lastError = (error as? APIError)?.errorDescription ?? error.localizedDescription
        }
    }
}
