# Renovation Planner — Claude Project File

## Platform & Toolchain

- **Target**: iPad, Swift Playgrounds 4.7 (Swift 6, iOS 26 SDK)
- **Format**: Single `.swiftpm` App project — open `RenovationPlanner.swiftpm` in Swift Playgrounds
- **UI framework**: SwiftUI only — no UIKit
- **Persistence**: SwiftData (`@Model`, `@Query`, `@Bindable`)
- **No external packages** — pure SwiftUI + Foundation + SwiftData

## File Layout

```
RenovationPlanner.swiftpm/
├── Package.swift
├── CLAUDE.md
└── Sources/
    └── App/
        └── RenovationPlanner.swift   ← all code lives here
```

All code is intentionally kept in a single file. If you split into multiple files, add them via the Playgrounds sidebar; no import statements are needed between files in the same module.

## Architecture

### Entry Point

```swift
@main
struct RenovationPlannerApp: App {
    var body: some Scene {
        WindowGroup { ContentView() }
        .modelContainer(for: [RenovationProject.self, Room.self, RenovationTask.self])
    }
}
```

### Navigation Structure

- `NavigationSplitView` at root (sidebar + detail) — correct iPad pattern
- Detail column wrapped in `NavigationStack` to enable push navigation with back buttons
- Navigation chain: `ContentView → ProjectDetailView → RoomDetailView → TaskDetailView`
- `ProjectDetailView` uses `TabView` with 3 tabs: Rooms, Budget, Settings

### Data Model (SwiftData)

```
RenovationProject   @Model
├── name: String
├── address: String
├── totalBudget: Double
├── startDate: Date
├── targetDate: Date
├── status: String                    ← ProjectStatus.rawValue
├── rooms: [Room]                     ← @Relationship(deleteRule: .cascade)
│
├── (computed) totalEstimatedCost: Double
├── (computed) totalActualCost: Double
├── (computed) budgetVariance: Double
├── (computed) isOverBudget: Bool
└── (computed) completionPercent: Double

Room                @Model
├── name: String
├── areaSqm: Double
├── tasks: [RenovationTask]           ← @Relationship(deleteRule: .cascade)
│
├── (computed) estimatedCost: Double
├── (computed) actualCost: Double
└── (computed) completionPercent: Double

RenovationTask      @Model
├── name: String
├── category: String                  ← TaskCategory.rawValue
├── status: String                    ← TaskStatus.rawValue
├── estimatedCost: Double
├── actualCost: Double?
├── contractor: String
├── notes: String
├── dueDate: Date?
└── (computed) costDelta: Double?     ← actualCost - estimatedCost, nil if no actual yet
```

### Enums

All enums are `String`-backed (`RawRepresentable`) for SwiftData compatibility.
**Do NOT change to non-String backing** — SwiftData cannot persist non-primitive enums directly.

```swift
enum TaskStatus: String, CaseIterable   // Planned | In Progress | Blocked | Done
enum TaskCategory: String, CaseIterable // Electrical | Plumbing | Tiling | Painting
                                        // Flooring | Carpentry | Structural | Other
enum ProjectStatus: String, CaseIterable // Planning | Active | On Hold | Complete
```

### Component Inventory

| Component            | Purpose                                                         |
|----------------------|-----------------------------------------------------------------|
| `BudgetSummaryCard`  | Estimated vs budget progress bar, room/task count, completion % |
| `RoomRow`            | Room name, estimated cost, task count, completion progress bar  |
| `TaskRow`            | Category icon, name, contractor, due date, cost, status pill    |
| `StatusPill`         | Colour-coded capsule label                                      |
| `BudgetRow`          | Label + R-formatted amount with configurable colour             |
| `AddRoomSheet`       | Room name text field + quick-pick grid of common room names     |
| `AddTaskSheet`       | Full task creation form with optional due date toggle           |
| `formatCurrency()`   | Free function, `NumberFormatter` decimal, no decimals           |

## Coding Constraints

### Currency

- South African Rand — prefix `R` (not a Unicode symbol, just the letter)
- `formatCurrency()` uses `NumberFormatter` with `maximumFractionDigits = 0`
- Example output: `R1 250 000`
- Usage: `"R\(formatCurrency(value))"` — the `R` prefix is NOT inside `formatCurrency`

### String Formatting

Never use `\(value, specifier:)` — it does not compile in Swift 6 Playgrounds.
Always use `String(format:)`:

```swift
// CORRECT
String(format: "%.1f m²", room.areaSqm)
"R\(formatCurrency(someDouble))"       // → "R1 250 000"

// WRONG — will not compile
"\(room.areaSqm, specifier: "%.1f") m²"
```

### SwiftData Patterns

- Use `@Query` in views to fetch top-level models
- Use `@Bindable` for in-place editing of `@Model` objects
- Use `@Environment(\.modelContext)` for insert/delete
- Cascade deletes are configured on all relationships
- **No manual `save()` calls** — SwiftData auto-saves on every change
- Appending to a relationship array (`project.rooms.append(room)`) is sufficient for insert;
  explicit `modelContext.insert()` is only needed for top-level objects

### Swift 6 Concurrency

- The project targets Swift 6 strict concurrency
- Avoid crossing actor boundaries with `@Model` objects
- Prefer `@MainActor`-bound access patterns if concurrency errors arise

### General Rules

- Do not use `specifier:` string interpolation
- Do not add CloudKit, multiple scenes, photos, notifications, or unit tests
- Do not add Info.plist customisation (not available in `.swiftpm` format)
- Do not introduce UIKit

## Typical Extension Points

- Add `@Relationship` materials list to `RenovationTask`
- Add photo attachment via `Data?` property on `Room` or `RenovationTask`
- Add a Dashboard view as a fourth sidebar item (tasks due this week)
- Add `Charts` framework donut/bar views for budget visualisation (available in Playgrounds)
