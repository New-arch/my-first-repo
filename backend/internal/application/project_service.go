package application

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/newarch/renovation-planner/internal/domain"
)

// ProjectService handles all project use cases.
type ProjectService struct {
	repo domain.ProjectRepository
}

// NewProjectService constructs a ProjectService with its required repository.
func NewProjectService(repo domain.ProjectRepository) *ProjectService {
	return &ProjectService{repo: repo}
}

// CreateProjectCommand carries the input data for creating a project.
type CreateProjectCommand struct {
	Name        string
	Address     string
	TotalBudget float64
	StartDate   time.Time
	TargetDate  time.Time
	Status      string
}

// UpdateProjectCommand carries the input data for updating a project.
type UpdateProjectCommand = CreateProjectCommand

func (s *ProjectService) ListProjects(ctx context.Context) ([]domain.Project, error) {
	return s.repo.FindAll(ctx)
}

func (s *ProjectService) GetProject(ctx context.Context, id string) (*domain.Project, error) {
	return s.repo.FindByIDWithRooms(ctx, id)
}

func (s *ProjectService) CreateProject(ctx context.Context, cmd CreateProjectCommand) (*domain.Project, error) {
	now := time.Now().UTC()
	p := &domain.Project{
		ID:          uuid.NewString(),
		Name:        cmd.Name,
		Address:     cmd.Address,
		TotalBudget: cmd.TotalBudget,
		StartDate:   cmd.StartDate,
		TargetDate:  cmd.TargetDate,
		Status:      domain.ProjectStatus(cmd.Status),
		CreatedAt:   now,
		UpdatedAt:   now,
	}

	if p.Status == "" {
		p.Status = domain.ProjectStatusPlanning
	}

	if err := p.Validate(); err != nil {
		return nil, fmt.Errorf("%w: %s", domain.ErrInvalidInput, err)
	}

	if err := s.repo.Create(ctx, p); err != nil {
		return nil, err
	}
	return p, nil
}

func (s *ProjectService) UpdateProject(ctx context.Context, id string, cmd UpdateProjectCommand) (*domain.Project, error) {
	p, err := s.repo.FindByID(ctx, id)
	if err != nil {
		return nil, err
	}

	p.Name = cmd.Name
	p.Address = cmd.Address
	p.TotalBudget = cmd.TotalBudget
	p.StartDate = cmd.StartDate
	p.TargetDate = cmd.TargetDate
	p.Status = domain.ProjectStatus(cmd.Status)
	p.UpdatedAt = time.Now().UTC()

	if err := p.Validate(); err != nil {
		return nil, fmt.Errorf("%w: %s", domain.ErrInvalidInput, err)
	}

	if err := s.repo.Update(ctx, p); err != nil {
		return nil, err
	}
	return p, nil
}

func (s *ProjectService) DeleteProject(ctx context.Context, id string) error {
	return s.repo.Delete(ctx, id)
}
