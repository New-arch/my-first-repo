package application

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/newarch/renovation-planner/internal/domain"
)

// RoomService handles all room use cases.
type RoomService struct {
	repo        domain.RoomRepository
	projectRepo domain.ProjectRepository
}

// NewRoomService constructs a RoomService with its required repositories.
func NewRoomService(repo domain.RoomRepository, projectRepo domain.ProjectRepository) *RoomService {
	return &RoomService{repo: repo, projectRepo: projectRepo}
}

// CreateRoomCommand carries the input data for creating a room.
type CreateRoomCommand struct {
	Name    string
	AreaSqm float64
}

// UpdateRoomCommand carries the input data for updating a room.
type UpdateRoomCommand = CreateRoomCommand

func (s *RoomService) ListRooms(ctx context.Context, projectID string) ([]domain.Room, error) {
	// Verify the parent project exists before listing.
	if _, err := s.projectRepo.FindByID(ctx, projectID); err != nil {
		return nil, err
	}
	return s.repo.FindByProjectID(ctx, projectID)
}

func (s *RoomService) GetRoom(ctx context.Context, id string) (*domain.Room, error) {
	return s.repo.FindByIDWithTasks(ctx, id)
}

func (s *RoomService) CreateRoom(ctx context.Context, projectID string, cmd CreateRoomCommand) (*domain.Room, error) {
	// Verify the parent project exists.
	if _, err := s.projectRepo.FindByID(ctx, projectID); err != nil {
		return nil, err
	}

	now := time.Now().UTC()
	r := &domain.Room{
		ID:        uuid.NewString(),
		ProjectID: projectID,
		Name:      cmd.Name,
		AreaSqm:   cmd.AreaSqm,
		CreatedAt: now,
		UpdatedAt: now,
	}

	if err := r.Validate(); err != nil {
		return nil, fmt.Errorf("%w: %s", domain.ErrInvalidInput, err)
	}

	if err := s.repo.Create(ctx, r); err != nil {
		return nil, err
	}
	return r, nil
}

func (s *RoomService) UpdateRoom(ctx context.Context, id string, cmd UpdateRoomCommand) (*domain.Room, error) {
	r, err := s.repo.FindByID(ctx, id)
	if err != nil {
		return nil, err
	}

	r.Name = cmd.Name
	r.AreaSqm = cmd.AreaSqm
	r.UpdatedAt = time.Now().UTC()

	if err := r.Validate(); err != nil {
		return nil, fmt.Errorf("%w: %s", domain.ErrInvalidInput, err)
	}

	if err := s.repo.Update(ctx, r); err != nil {
		return nil, err
	}
	return r, nil
}

func (s *RoomService) DeleteRoom(ctx context.Context, id string) error {
	return s.repo.Delete(ctx, id)
}
