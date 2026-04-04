package domain

import "context"

// ProjectRepository defines all persistence operations for the Project aggregate.
// Only this package is allowed to implement this interface — infrastructure
// packages depend inward on domain, never the reverse.
type ProjectRepository interface {
	FindAll(ctx context.Context) ([]Project, error)
	FindByID(ctx context.Context, id string) (*Project, error)
	// FindByIDWithRooms returns a project with its Rooms and Tasks eagerly loaded.
	FindByIDWithRooms(ctx context.Context, id string) (*Project, error)
	Create(ctx context.Context, p *Project) error
	Update(ctx context.Context, p *Project) error
	Delete(ctx context.Context, id string) error
}

// RoomRepository defines all persistence operations for Rooms.
type RoomRepository interface {
	FindByProjectID(ctx context.Context, projectID string) ([]Room, error)
	FindByID(ctx context.Context, id string) (*Room, error)
	// FindByIDWithTasks returns a room with its Tasks eagerly loaded.
	FindByIDWithTasks(ctx context.Context, id string) (*Room, error)
	Create(ctx context.Context, r *Room) error
	Update(ctx context.Context, r *Room) error
	Delete(ctx context.Context, id string) error
}

// TaskRepository defines all persistence operations for RenovationTasks.
type TaskRepository interface {
	FindByRoomID(ctx context.Context, roomID string) ([]RenovationTask, error)
	FindByID(ctx context.Context, id string) (*RenovationTask, error)
	Create(ctx context.Context, t *RenovationTask) error
	Update(ctx context.Context, t *RenovationTask) error
	Delete(ctx context.Context, id string) error
}
