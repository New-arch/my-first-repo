package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/newarch/renovation-planner/internal/domain"
)

type projectRepository struct {
	db *DB
}

// NewProjectRepository returns a SQLite-backed ProjectRepository.
func NewProjectRepository(db *DB) domain.ProjectRepository {
	return &projectRepository{db: db}
}

func (r *projectRepository) FindAll(ctx context.Context) ([]domain.Project, error) {
	const q = `SELECT id, name, address, total_budget, start_date, target_date,
	                  status, created_at, updated_at
	           FROM projects ORDER BY name`

	rows, err := r.db.QueryContext(ctx, q)
	if err != nil {
		return nil, fmt.Errorf("projects.FindAll query: %w", err)
	}
	defer rows.Close()

	var projects []domain.Project
	for rows.Next() {
		p, err := scanProject(rows)
		if err != nil {
			return nil, err
		}
		projects = append(projects, p)
	}
	return projects, rows.Err()
}

func (r *projectRepository) FindByID(ctx context.Context, id string) (*domain.Project, error) {
	const q = `SELECT id, name, address, total_budget, start_date, target_date,
	                  status, created_at, updated_at
	           FROM projects WHERE id = ?`

	row := r.db.QueryRowContext(ctx, q, id)
	p, err := scanProject(row)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, domain.ErrNotFound
		}
		return nil, fmt.Errorf("projects.FindByID: %w", err)
	}
	return &p, nil
}

func (r *projectRepository) FindByIDWithRooms(ctx context.Context, id string) (*domain.Project, error) {
	p, err := r.FindByID(ctx, id)
	if err != nil {
		return nil, err
	}

	roomRepo := &roomRepository{db: r.db}
	rooms, err := roomRepo.FindByProjectID(ctx, id)
	if err != nil {
		return nil, err
	}

	taskRepo := &taskRepository{db: r.db}
	for i := range rooms {
		tasks, err := taskRepo.FindByRoomID(ctx, rooms[i].ID)
		if err != nil {
			return nil, err
		}
		rooms[i].Tasks = tasks
	}
	p.Rooms = rooms
	return p, nil
}

func (r *projectRepository) Create(ctx context.Context, p *domain.Project) error {
	const q = `INSERT INTO projects
		(id, name, address, total_budget, start_date, target_date, status, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`

	_, err := r.db.ExecContext(ctx, q,
		p.ID, p.Name, p.Address, p.TotalBudget,
		p.StartDate.UTC().Format(time.RFC3339),
		p.TargetDate.UTC().Format(time.RFC3339),
		string(p.Status),
		p.CreatedAt.UTC().Format(time.RFC3339),
		p.UpdatedAt.UTC().Format(time.RFC3339),
	)
	if err != nil {
		return fmt.Errorf("projects.Create: %w", err)
	}
	return nil
}

func (r *projectRepository) Update(ctx context.Context, p *domain.Project) error {
	const q = `UPDATE projects
		SET name=?, address=?, total_budget=?, start_date=?, target_date=?, status=?, updated_at=?
		WHERE id=?`

	res, err := r.db.ExecContext(ctx, q,
		p.Name, p.Address, p.TotalBudget,
		p.StartDate.UTC().Format(time.RFC3339),
		p.TargetDate.UTC().Format(time.RFC3339),
		string(p.Status),
		p.UpdatedAt.UTC().Format(time.RFC3339),
		p.ID,
	)
	if err != nil {
		return fmt.Errorf("projects.Update: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("projects.Update rows affected: %w", err)
	}
	if n == 0 {
		return domain.ErrNotFound
	}
	return nil
}

func (r *projectRepository) Delete(ctx context.Context, id string) error {
	const q = `DELETE FROM projects WHERE id=?`
	res, err := r.db.ExecContext(ctx, q, id)
	if err != nil {
		return fmt.Errorf("projects.Delete: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("projects.Delete rows affected: %w", err)
	}
	if n == 0 {
		return domain.ErrNotFound
	}
	return nil
}

// ---- helpers ----------------------------------------------------------------

type scanner interface {
	Scan(dest ...any) error
}

func scanProject(s scanner) (domain.Project, error) {
	var p domain.Project
	var startDate, targetDate, createdAt, updatedAt string
	var status string

	err := s.Scan(
		&p.ID, &p.Name, &p.Address, &p.TotalBudget,
		&startDate, &targetDate, &status,
		&createdAt, &updatedAt,
	)
	if err != nil {
		return p, err
	}

	p.Status = domain.ProjectStatus(status)
	p.StartDate, _ = time.Parse(time.RFC3339, startDate)
	p.TargetDate, _ = time.Parse(time.RFC3339, targetDate)
	p.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
	p.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
	return p, nil
}
