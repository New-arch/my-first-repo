package application

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/newarch/renovation-planner/internal/domain"
)

// TaskService handles all renovation task use cases.
type TaskService struct {
	repo     domain.TaskRepository
	roomRepo domain.RoomRepository
}

// NewTaskService constructs a TaskService with its required repositories.
func NewTaskService(repo domain.TaskRepository, roomRepo domain.RoomRepository) *TaskService {
	return &TaskService{repo: repo, roomRepo: roomRepo}
}

// CreateTaskCommand carries the input data for creating a task.
type CreateTaskCommand struct {
	Name          string
	Category      string
	Status        string
	EstimatedCost float64
	ActualCost    *float64
	Contractor    string
	Notes         string
	DueDate       *time.Time
}

// UpdateTaskCommand carries the input data for updating a task.
type UpdateTaskCommand = CreateTaskCommand

func (s *TaskService) ListTasks(ctx context.Context, roomID string) ([]domain.RenovationTask, error) {
	// Verify the parent room exists before listing.
	if _, err := s.roomRepo.FindByID(ctx, roomID); err != nil {
		return nil, err
	}
	return s.repo.FindByRoomID(ctx, roomID)
}

func (s *TaskService) GetTask(ctx context.Context, id string) (*domain.RenovationTask, error) {
	return s.repo.FindByID(ctx, id)
}

func (s *TaskService) CreateTask(ctx context.Context, roomID string, cmd CreateTaskCommand) (*domain.RenovationTask, error) {
	// Verify the parent room exists.
	if _, err := s.roomRepo.FindByID(ctx, roomID); err != nil {
		return nil, err
	}

	now := time.Now().UTC()
	category := domain.TaskCategory(cmd.Category)
	if category == "" {
		category = domain.TaskCategoryOther
	}
	status := domain.TaskStatus(cmd.Status)
	if status == "" {
		status = domain.TaskStatusPlanned
	}

	t := &domain.RenovationTask{
		ID:            uuid.NewString(),
		RoomID:        roomID,
		Name:          cmd.Name,
		Category:      category,
		Status:        status,
		EstimatedCost: cmd.EstimatedCost,
		ActualCost:    cmd.ActualCost,
		Contractor:    cmd.Contractor,
		Notes:         cmd.Notes,
		DueDate:       cmd.DueDate,
		CreatedAt:     now,
		UpdatedAt:     now,
	}

	if err := t.Validate(); err != nil {
		return nil, fmt.Errorf("%w: %s", domain.ErrInvalidInput, err)
	}

	if err := s.repo.Create(ctx, t); err != nil {
		return nil, err
	}
	return t, nil
}

func (s *TaskService) UpdateTask(ctx context.Context, id string, cmd UpdateTaskCommand) (*domain.RenovationTask, error) {
	t, err := s.repo.FindByID(ctx, id)
	if err != nil {
		return nil, err
	}

	t.Name = cmd.Name
	t.Category = domain.TaskCategory(cmd.Category)
	t.Status = domain.TaskStatus(cmd.Status)
	t.EstimatedCost = cmd.EstimatedCost
	t.ActualCost = cmd.ActualCost
	t.Contractor = cmd.Contractor
	t.Notes = cmd.Notes
	t.DueDate = cmd.DueDate
	t.UpdatedAt = time.Now().UTC()

	if err := t.Validate(); err != nil {
		return nil, fmt.Errorf("%w: %s", domain.ErrInvalidInput, err)
	}

	if err := s.repo.Update(ctx, t); err != nil {
		return nil, err
	}
	return t, nil
}

func (s *TaskService) DeleteTask(ctx context.Context, id string) error {
	return s.repo.Delete(ctx, id)
}
