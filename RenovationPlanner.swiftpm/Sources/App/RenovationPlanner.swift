import SwiftUI
import SwiftData

// ============================================================
// MARK: - DATA MODELS
// ============================================================

@Model
class RenovationProject {
    var name: String
    var address: String
    var totalBudget: Double
    var startDate: Date
    var targetDate: Date
    var status: String              // "Planning" | "Active" | "On Hold" | "Complete"

    @Relationship(deleteRule: .cascade)
    var rooms: [Room] = []

    init(
        name: String,
        address: String = "",
        totalBudget: Double = 0,
        startDate: Date = .now,
        targetDate: Date = Calendar.current.date(byAdding: .month, value: 3, to: .now) ?? .now,
        status: String = "Planning"
    ) {
        self.name = name
        self.address = address
        self.totalBudget = totalBudget
        self.startDate = startDate
        self.targetDate = targetDate
        self.status = status
    }

    var totalEstimatedCost: Double {
        rooms.flatMap { $0.tasks }.reduce(0) { $0 + $1.estimatedCost }
    }

    var totalActualCost: Double {
        rooms.flatMap { $0.tasks }.reduce(0) { $0 + ($1.actualCost ?? 0) }
    }

    var budgetVariance: Double { totalBudget - totalEstimatedCost }
    var isOverBudget: Bool { totalEstimatedCost > totalBudget && totalBudget > 0 }

    var completionPercent: Double {
        let allTasks = rooms.flatMap { $0.tasks }
        guard !allTasks.isEmpty else { return 0 }
        let done = allTasks.filter { $0.status == TaskStatus.done.rawValue }.count
        return Double(done) / Double(allTasks.count) * 100
    }
}

@Model
class Room {
    var name: String
    var areaSqm: Double

    @Relationship(deleteRule: .cascade)
    var tasks: [RenovationTask] = []

    init(name: String, areaSqm: Double = 0) {
        self.name = name
        self.areaSqm = areaSqm
    }

    var estimatedCost: Double { tasks.reduce(0) { $0 + $1.estimatedCost } }
    var actualCost: Double { tasks.reduce(0) { $0 + ($1.actualCost ?? 0) } }

    var completionPercent: Double {
        guard !tasks.isEmpty else { return 0 }
        let done = tasks.filter { $0.status == TaskStatus.done.rawValue }.count
        return Double(done) / Double(tasks.count) * 100
    }
}

@Model
class RenovationTask {
    var name: String
    var category: String            // TaskCategory raw values
    var status: String              // TaskStatus raw values
    var estimatedCost: Double
    var actualCost: Double?
    var contractor: String
    var notes: String
    var dueDate: Date?

    init(
        name: String,
        category: String = TaskCategory.other.rawValue,
        status: String = TaskStatus.planned.rawValue,
        estimatedCost: Double = 0,
        contractor: String = "",
        notes: String = ""
    ) {
        self.name = name
        self.category = category
        self.status = status
        self.estimatedCost = estimatedCost
        self.contractor = contractor
        self.notes = notes
    }

    var costDelta: Double? {
        guard let actual = actualCost else { return nil }
        return actual - estimatedCost
    }
}

// ============================================================
// MARK: - ENUMS (String-backed for SwiftData compatibility)
// ============================================================

enum TaskStatus: String, CaseIterable {
    case planned    = "Planned"
    case inProgress = "In Progress"
    case blocked    = "Blocked"
    case done       = "Done"

    var color: Color {
        switch self {
        case .planned:    return .gray
        case .inProgress: return .blue
        case .blocked:    return .red
        case .done:       return .green
        }
    }
}

enum TaskCategory: String, CaseIterable {
    case electrical = "Electrical"
    case plumbing   = "Plumbing"
    case tiling     = "Tiling"
    case painting   = "Painting"
    case flooring   = "Flooring"
    case carpentry  = "Carpentry"
    case structural = "Structural"
    case other      = "Other"

    var icon: String {
        switch self {
        case .electrical: return "bolt.fill"
        case .plumbing:   return "drop.fill"
        case .tiling:     return "square.grid.3x3.fill"
        case .painting:   return "paintbrush.fill"
        case .flooring:   return "square.fill.on.square.fill"
        case .carpentry:  return "hammer.fill"
        case .structural: return "building.2.fill"
        case .other:      return "wrench.fill"
        }
    }
}

enum ProjectStatus: String, CaseIterable {
    case planning = "Planning"
    case active   = "Active"
    case onHold   = "On Hold"
    case complete = "Complete"

    var color: Color {
        switch self {
        case .planning: return .gray
        case .active:   return .green
        case .onHold:   return .orange
        case .complete: return .blue
        }
    }
}

// ============================================================
// MARK: - APP ENTRY POINT
// ============================================================

@main
struct RenovationPlannerApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(for: [RenovationProject.self, Room.self, RenovationTask.self])
    }
}

// ============================================================
// MARK: - ROOT CONTENT VIEW
// ============================================================

struct ContentView: View {
    @Query(sort: \RenovationProject.name) var projects: [RenovationProject]
    @Environment(\.modelContext) var modelContext

    @State private var selectedProject: RenovationProject?
    @State private var showingAddProject = false

    var body: some View {
        NavigationSplitView {
            // ── Sidebar ──────────────────────────────────────
            List(selection: $selectedProject) {
                if projects.isEmpty {
                    ContentUnavailableView(
                        "No Projects",
                        systemImage: "house.badge.plus",
                        description: Text("Tap + to add your first renovation project.")
                    )
                } else {
                    ForEach(projects) { project in
                        ProjectRow(project: project)
                            .tag(project)
                    }
                    .onDelete(perform: deleteProjects)
                }
            }
            .navigationTitle("Renovations")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button { showingAddProject = true } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showingAddProject) {
                AddProjectSheet()
            }

        } detail: {
            // ── Detail pane ──────────────────────────────────
            if let project = selectedProject {
                NavigationStack {
                    ProjectDetailView(project: project)
                }
            } else {
                ContentUnavailableView(
                    "Select a Project",
                    systemImage: "house.fill",
                    description: Text("Choose a renovation project from the sidebar.")
                )
            }
        }
    }

    func deleteProjects(at offsets: IndexSet) {
        for index in offsets { modelContext.delete(projects[index]) }
    }
}

// ============================================================
// MARK: - PROJECT ROW (Sidebar cell)
// ============================================================

struct ProjectRow: View {
    let project: RenovationProject

    var statusEnum: ProjectStatus { ProjectStatus(rawValue: project.status) ?? .planning }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(project.name).font(.headline)
                Spacer()
                StatusPill(label: project.status, color: statusEnum.color)
            }
            HStack(spacing: 12) {
                Label("\(project.rooms.count) rooms", systemImage: "door.left.hand.open")
                    .font(.caption).foregroundStyle(.secondary)
                if project.totalEstimatedCost > 0 {
                    Label("R\(formatCurrency(project.totalEstimatedCost))", systemImage: "banknote")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            if !project.rooms.flatMap({ $0.tasks }).isEmpty {
                ProgressView(value: project.completionPercent / 100)
                    .tint(.green)
            }
        }
        .padding(.vertical, 4)
    }
}

// ============================================================
// MARK: - ADD PROJECT SHEET
// ============================================================

struct AddProjectSheet: View {
    @Environment(\.modelContext) var modelContext
    @Environment(\.dismiss) var dismiss

    @State private var name = ""
    @State private var address = ""
    @State private var budget = ""
    @State private var status = ProjectStatus.planning.rawValue
    @State private var startDate = Date.now
    @State private var targetDate = Calendar.current.date(byAdding: .month, value: 3, to: .now) ?? .now

    var body: some View {
        NavigationStack {
            Form {
                Section("Details") {
                    TextField("Project name", text: $name)
                    TextField("Address", text: $address)
                }
                Section("Budget") {
                    HStack {
                        Text("R")
                        TextField("Total budget", text: $budget)
                            .keyboardType(.decimalPad)
                    }
                }
                Section("Dates") {
                    DatePicker("Start", selection: $startDate, displayedComponents: .date)
                    DatePicker("Target completion", selection: $targetDate, displayedComponents: .date)
                }
                Section("Status") {
                    Picker("Status", selection: $status) {
                        ForEach(ProjectStatus.allCases, id: \.rawValue) { s in
                            Text(s.rawValue).tag(s.rawValue)
                        }
                    }
                    .pickerStyle(.segmented)
                }
            }
            .navigationTitle("New Project")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") { save() }
                        .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }

    func save() {
        let project = RenovationProject(
            name: name.trimmingCharacters(in: .whitespaces),
            address: address,
            totalBudget: Double(budget) ?? 0,
            startDate: startDate,
            targetDate: targetDate,
            status: status
        )
        modelContext.insert(project)
        dismiss()
    }
}

// ============================================================
// MARK: - PROJECT DETAIL VIEW
// ============================================================

struct ProjectDetailView: View {
    @Bindable var project: RenovationProject
    @Environment(\.modelContext) var modelContext

    @State private var showingAddRoom = false
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {

            // ── Tab 1: Rooms ─────────────────────────────────
            RoomsTab(project: project)
                .tabItem { Label("Rooms", systemImage: "door.left.hand.open") }
                .tag(0)

            // ── Tab 2: Budget ────────────────────────────────
            BudgetTab(project: project)
                .tabItem { Label("Budget", systemImage: "banknote") }
                .tag(1)

            // ── Tab 3: Settings ──────────────────────────────
            ProjectSettingsTab(project: project)
                .tabItem { Label("Settings", systemImage: "gear") }
                .tag(2)
        }
        .navigationTitle(project.name)
        .navigationBarTitleDisplayMode(.large)
    }
}

// ============================================================
// MARK: - ROOMS TAB
// ============================================================

struct RoomsTab: View {
    @Bindable var project: RenovationProject
    @Environment(\.modelContext) var modelContext
    @State private var showingAddRoom = false

    var body: some View {
        List {
            // Summary card
            Section {
                BudgetSummaryCard(project: project)
            }

            // Rooms list
            Section {
                ForEach(project.rooms) { room in
                    NavigationLink(destination: RoomDetailView(room: room)) {
                        RoomRow(room: room)
                    }
                }
                .onDelete { offsets in
                    for idx in offsets { modelContext.delete(project.rooms[idx]) }
                }
            } header: {
                HStack {
                    Text("Rooms (\(project.rooms.count))")
                    Spacer()
                    Button { showingAddRoom = true } label: {
                        Image(systemName: "plus.circle.fill").foregroundStyle(.blue)
                    }
                }
            }

            if project.rooms.isEmpty {
                ContentUnavailableView(
                    "No Rooms Yet",
                    systemImage: "square.dashed",
                    description: Text("Tap + above to add a room.")
                )
            }
        }
        .sheet(isPresented: $showingAddRoom) {
            AddRoomSheet(project: project)
        }
    }
}

// ============================================================
// MARK: - BUDGET TAB
// ============================================================

struct BudgetTab: View {
    let project: RenovationProject

    var body: some View {
        List {
            // Overall
            Section("Overall") {
                BudgetRow(label: "Total Budget",   amount: project.totalBudget,        color: .primary)
                BudgetRow(label: "Estimated Cost", amount: project.totalEstimatedCost, color: project.isOverBudget ? .red : .primary)
                BudgetRow(label: "Actual Spend",   amount: project.totalActualCost,    color: .primary)
                HStack {
                    Text("Variance")
                    Spacer()
                    Text(project.budgetVariance >= 0
                         ? "+R\(formatCurrency(project.budgetVariance))"
                         : "-R\(formatCurrency(abs(project.budgetVariance)))")
                    .font(.subheadline.bold())
                    .foregroundStyle(project.budgetVariance >= 0 ? .green : .red)
                }
            }

            // Per-room breakdown
            Section("By Room") {
                ForEach(project.rooms) { room in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(room.name).font(.subheadline.bold())
                            Spacer()
                            Text("R\(formatCurrency(room.estimatedCost))").font(.subheadline)
                        }
                        if room.estimatedCost > 0 && project.totalEstimatedCost > 0 {
                            let fraction = room.estimatedCost / project.totalEstimatedCost
                            ProgressView(value: fraction)
                                .tint(.blue)
                            Text("\(Int(fraction * 100))% of total estimate")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }

            // Category totals across all rooms
            Section("By Category") {
                ForEach(TaskCategory.allCases, id: \.rawValue) { cat in
                    let total = project.rooms
                        .flatMap { $0.tasks }
                        .filter { $0.category == cat.rawValue }
                        .reduce(0) { $0 + $1.estimatedCost }
                    if total > 0 {
                        HStack {
                            Label(cat.rawValue, systemImage: cat.icon)
                                .font(.subheadline)
                            Spacer()
                            Text("R\(formatCurrency(total))").font(.subheadline)
                        }
                    }
                }
            }
        }
        .navigationTitle("Budget")
    }
}

// ============================================================
// MARK: - PROJECT SETTINGS TAB
// ============================================================

struct ProjectSettingsTab: View {
    @Bindable var project: RenovationProject

    var body: some View {
        Form {
            Section("Details") {
                TextField("Name", text: $project.name)
                TextField("Address", text: $project.address)
            }
            Section("Budget") {
                HStack {
                    Text("R")
                    TextField("Budget", value: $project.totalBudget, format: .number)
                        .keyboardType(.decimalPad)
                }
            }
            Section("Dates") {
                DatePicker("Start", selection: $project.startDate, displayedComponents: .date)
                DatePicker("Target", selection: $project.targetDate, displayedComponents: .date)
            }
            Section("Status") {
                Picker("Status", selection: $project.status) {
                    ForEach(ProjectStatus.allCases, id: \.rawValue) { s in
                        Text(s.rawValue).tag(s.rawValue)
                    }
                }
                .pickerStyle(.segmented)
            }
            Section("Summary") {
                LabeledContent("Rooms", value: "\(project.rooms.count)")
                LabeledContent("Tasks", value: "\(project.rooms.flatMap { $0.tasks }.count)")
                LabeledContent("Completion", value: "\(Int(project.completionPercent))%")
            }
        }
        .navigationTitle("Settings")
    }
}

// ============================================================
// MARK: - ROOM DETAIL VIEW
// ============================================================

struct RoomDetailView: View {
    @Bindable var room: Room
    @Environment(\.modelContext) var modelContext
    @State private var showingAddTask = false

    var body: some View {
        List {
            // Room stats
            Section("Room") {
                LabeledContent("Area", value: String(format: "%.1f m²", room.areaSqm))
                LabeledContent("Estimated Cost", value: "R\(formatCurrency(room.estimatedCost))")
                LabeledContent("Actual Spend",   value: "R\(formatCurrency(room.actualCost))")
                LabeledContent("Completion",     value: "\(Int(room.completionPercent))%")
                if !room.tasks.isEmpty {
                    ProgressView(value: room.completionPercent / 100).tint(.green)
                }
            }

            // Tasks grouped by category
            ForEach(TaskCategory.allCases, id: \.rawValue) { cat in
                let catTasks = room.tasks.filter { $0.category == cat.rawValue }
                if !catTasks.isEmpty {
                    Section {
                        ForEach(catTasks) { task in
                            NavigationLink(destination: TaskDetailView(task: task)) {
                                TaskRow(task: task)
                            }
                            .swipeActions(edge: .trailing) {
                                Button(role: .destructive) {
                                    modelContext.delete(task)
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                            .swipeActions(edge: .leading) {
                                Button {
                                    task.status = TaskStatus.done.rawValue
                                } label: {
                                    Label("Done", systemImage: "checkmark.circle")
                                }
                                .tint(.green)
                            }
                        }
                    } header: {
                        Label(cat.rawValue, systemImage: cat.icon)
                    }
                }
            }

            if room.tasks.isEmpty {
                ContentUnavailableView(
                    "No Tasks",
                    systemImage: "list.bullet.clipboard",
                    description: Text("Tap + to add tasks to this room.")
                )
            }
        }
        .navigationTitle(room.name)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button { showingAddTask = true } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .sheet(isPresented: $showingAddTask) {
            AddTaskSheet(room: room)
        }
    }
}

// ============================================================
// MARK: - TASK DETAIL VIEW
// ============================================================

struct TaskDetailView: View {
    @Bindable var task: RenovationTask

    var body: some View {
        Form {
            Section("Task") {
                TextField("Name", text: $task.name)
                Picker("Category", selection: $task.category) {
                    ForEach(TaskCategory.allCases, id: \.rawValue) { c in
                        Label(c.rawValue, systemImage: c.icon).tag(c.rawValue)
                    }
                }
                Picker("Status", selection: $task.status) {
                    ForEach(TaskStatus.allCases, id: \.rawValue) { s in
                        Text(s.rawValue).tag(s.rawValue)
                    }
                }
            }
            Section("Cost") {
                HStack {
                    Text("Estimated  R")
                    TextField("0", value: $task.estimatedCost, format: .number)
                        .keyboardType(.decimalPad)
                }
                HStack {
                    Text("Actual       R")
                    TextField("Not yet", value: $task.actualCost, format: .number)
                        .keyboardType(.decimalPad)
                }
                if let delta = task.costDelta {
                    HStack {
                        Text("Variance")
                        Spacer()
                        Text(delta >= 0
                             ? "+R\(formatCurrency(delta))"
                             : "-R\(formatCurrency(abs(delta)))")
                        .foregroundStyle(delta <= 0 ? .green : .red)
                        .bold()
                    }
                }
            }
            Section("Contractor") {
                TextField("Contractor / supplier", text: $task.contractor)
            }
            Section("Due Date") {
                if let due = task.dueDate {
                    DatePicker("Due date", selection: Binding(
                        get: { due },
                        set: { task.dueDate = $0 }
                    ), displayedComponents: .date)
                    Button("Remove due date", role: .destructive) { task.dueDate = nil }
                } else {
                    Button("Set due date") {
                        task.dueDate = .now
                    }
                }
            }
            Section("Notes") {
                TextField("Notes", text: $task.notes, axis: .vertical)
                    .lineLimit(4...)
            }
        }
        .navigationTitle(task.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}

// ============================================================
// MARK: - REUSABLE COMPONENTS
// ============================================================

struct BudgetSummaryCard: View {
    let project: RenovationProject

    var fraction: Double {
        guard project.totalBudget > 0 else { return 0 }
        return min(project.totalEstimatedCost / project.totalBudget, 1.0)
    }

    var barColor: Color {
        fraction > 1.0 ? .red : fraction > 0.8 ? .orange : .green
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Estimated").font(.caption).foregroundStyle(.secondary)
                    Text("R\(formatCurrency(project.totalEstimatedCost))").font(.title2.bold())
                        .foregroundStyle(project.isOverBudget ? .red : .primary)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 2) {
                    Text("Budget").font(.caption).foregroundStyle(.secondary)
                    Text("R\(formatCurrency(project.totalBudget))").font(.title2.bold())
                }
            }

            ProgressView(value: fraction).tint(barColor)

            HStack {
                Text("\(project.rooms.count) rooms · \(project.rooms.flatMap { $0.tasks }.count) tasks")
                    .font(.caption).foregroundStyle(.secondary)
                Spacer()
                Text("\(Int(project.completionPercent))% complete")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}

struct RoomRow: View {
    let room: Room

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(room.name).font(.headline)
                Spacer()
                Text("R\(formatCurrency(room.estimatedCost))")
                    .font(.subheadline.bold()).foregroundStyle(.blue)
            }
            HStack {
                Text("\(room.tasks.count) tasks")
                    .font(.caption).foregroundStyle(.secondary)
                Spacer()
                if !room.tasks.isEmpty {
                    Text("\(Int(room.completionPercent))% done")
                        .font(.caption)
                        .foregroundStyle(room.completionPercent == 100 ? .green : .secondary)
                }
            }
            if !room.tasks.isEmpty {
                ProgressView(value: room.completionPercent / 100).tint(.green)
            }
        }
        .padding(.vertical, 4)
    }
}

struct TaskRow: View {
    let task: RenovationTask

    var statusEnum: TaskStatus { TaskStatus(rawValue: task.status) ?? .planned }
    var categoryEnum: TaskCategory { TaskCategory(rawValue: task.category) ?? .other }

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: categoryEnum.icon)
                .foregroundStyle(.blue)
                .frame(width: 22)

            VStack(alignment: .leading, spacing: 2) {
                Text(task.name).font(.subheadline)
                HStack(spacing: 8) {
                    if !task.contractor.isEmpty {
                        Text(task.contractor).font(.caption2).foregroundStyle(.secondary)
                    }
                    if let due = task.dueDate {
                        Text(due, style: .date).font(.caption2).foregroundStyle(.secondary)
                    }
                }
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text("R\(formatCurrency(task.estimatedCost))").font(.subheadline.bold())
                StatusPill(label: task.status, color: statusEnum.color)
            }
        }
        .padding(.vertical, 2)
    }
}

struct AddRoomSheet: View {
    let project: RenovationProject
    @Environment(\.dismiss) var dismiss

    @State private var name = ""
    @State private var area = ""

    let suggestions = ["Kitchen", "Living Room", "Master Bedroom", "Bedroom",
                       "Bathroom", "En-suite", "Garage", "Garden", "Study", "Dining Room"]

    var body: some View {
        NavigationStack {
            Form {
                Section("Room Name") {
                    TextField("e.g. Kitchen", text: $name)
                }
                Section("Quick Pick") {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 110))], spacing: 8) {
                        ForEach(suggestions, id: \.self) { s in
                            Button(s) { name = s }
                                .buttonStyle(.bordered)
                                .font(.caption)
                        }
                    }
                    .padding(.vertical, 4)
                }
                Section("Floor Area") {
                    HStack {
                        TextField("0", text: $area)
                            .keyboardType(.decimalPad)
                        Text("m²")
                    }
                }
            }
            .navigationTitle("New Room")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        let room = Room(name: name.isEmpty ? "Room" : name,
                                       areaSqm: Double(area) ?? 0)
                        project.rooms.append(room)
                        dismiss()
                    }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}

struct AddTaskSheet: View {
    let room: Room
    @Environment(\.dismiss) var dismiss

    @State private var name = ""
    @State private var category = TaskCategory.other.rawValue
    @State private var status   = TaskStatus.planned.rawValue
    @State private var estimatedCost = ""
    @State private var contractor = ""
    @State private var notes = ""
    @State private var hasDueDate = false
    @State private var dueDate = Date.now

    var body: some View {
        NavigationStack {
            Form {
                Section("Task") {
                    TextField("Task name", text: $name)
                    Picker("Category", selection: $category) {
                        ForEach(TaskCategory.allCases, id: \.rawValue) { c in
                            Label(c.rawValue, systemImage: c.icon).tag(c.rawValue)
                        }
                    }
                    Picker("Status", selection: $status) {
                        ForEach(TaskStatus.allCases, id: \.rawValue) { s in
                            Text(s.rawValue).tag(s.rawValue)
                        }
                    }
                }
                Section("Cost (R)") {
                    TextField("Estimated cost", text: $estimatedCost)
                        .keyboardType(.decimalPad)
                }
                Section("Contractor") {
                    TextField("Contractor / supplier (optional)", text: $contractor)
                }
                Section("Due Date") {
                    Toggle("Set due date", isOn: $hasDueDate)
                    if hasDueDate {
                        DatePicker("Date", selection: $dueDate, displayedComponents: .date)
                    }
                }
                Section("Notes") {
                    TextField("Notes (optional)", text: $notes, axis: .vertical)
                        .lineLimit(3...)
                }
            }
            .navigationTitle("New Task")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        let task = RenovationTask(
                            name: name.trimmingCharacters(in: .whitespaces),
                            category: category,
                            status: status,
                            estimatedCost: Double(estimatedCost) ?? 0,
                            contractor: contractor,
                            notes: notes
                        )
                        if hasDueDate { task.dueDate = dueDate }
                        room.tasks.append(task)
                        dismiss()
                    }
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}

struct StatusPill: View {
    let label: String
    let color: Color

    var body: some View {
        Text(label)
            .font(.caption2)
            .padding(.horizontal, 7)
            .padding(.vertical, 2)
            .background(color.opacity(0.15))
            .foregroundStyle(color)
            .clipShape(Capsule())
    }
}

struct BudgetRow: View {
    let label: String
    let amount: Double
    let color: Color

    var body: some View {
        HStack {
            Text(label)
            Spacer()
            Text("R\(formatCurrency(amount))").font(.subheadline).foregroundStyle(color)
        }
    }
}

// ============================================================
// MARK: - UTILITIES
// ============================================================

func formatCurrency(_ value: Double) -> String {
    let formatter = NumberFormatter()
    formatter.numberStyle = .decimal
    formatter.maximumFractionDigits = 0
    return formatter.string(from: NSNumber(value: value)) ?? "\(Int(value))"
}
