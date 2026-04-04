package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/newarch/renovation-planner/internal/domain"
)

type taskRepository struct {
	db *DB
}

// NewTaskRepository returns a SQLite-backed TaskRepository.
func NewTaskRepository(db *DB) domain.TaskRepository {
	return &taskRepository{db: db}
}

func (r *taskRepository) FindByRoomID(ctx context.Context, roomID string) ([]domain.RenovationTask, error) {
	const q = `SELECT id, room_id, name, category, status, estimated_cost, actual_cost,
	                  contractor, notes, due_date, created_at, updated_at
	           FROM tasks WHERE room_id = ? ORDER BY name`

	rows, err := r.db.QueryContext(ctx, q, roomID)
	if err != nil {
		return nil, fmt.Errorf("tasks.FindByRoomID query: %w", err)
	}
	defer rows.Close()

	var tasks []domain.RenovationTask
	for rows.Next() {
		t, err := scanTask(rows)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, t)
	}
	return tasks, rows.Err()
}

func (r *taskRepository) FindByID(ctx context.Context, id string) (*domain.RenovationTask, error) {
	const q = `SELECT id, room_id, name, category, status, estimated_cost, actual_cost,
	                  contractor, notes, due_date, created_at, updated_at
	           FROM tasks WHERE id = ?`

	row := r.db.QueryRowContext(ctx, q, id)
	t, err := scanTask(row)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, domain.ErrNotFound
		}
		return nil, fmt.Errorf("tasks.FindByID: %w", err)
	}
	return &t, nil
}

func (r *taskRepository) Create(ctx context.Context, t *domain.RenovationTask) error {
	const q = `INSERT INTO tasks
		(id, room_id, name, category, status, estimated_cost, actual_cost,
		 contractor, notes, due_date, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`

	_, err := r.db.ExecContext(ctx, q,
		t.ID, t.RoomID, t.Name,
		string(t.Category), string(t.Status),
		t.EstimatedCost, t.ActualCost,
		t.Contractor, t.Notes,
		formatNullableTime(t.DueDate),
		t.CreatedAt.UTC().Format(time.RFC3339),
		t.UpdatedAt.UTC().Format(time.RFC3339),
	)
	if err != nil {
		return fmt.Errorf("tasks.Create: %w", err)
	}
	return nil
}

func (r *taskRepository) Update(ctx context.Context, t *domain.RenovationTask) error {
	const q = `UPDATE tasks
		SET name=?, category=?, status=?, estimated_cost=?, actual_cost=?,
		    contractor=?, notes=?, due_date=?, updated_at=?
		WHERE id=?`

	res, err := r.db.ExecContext(ctx, q,
		t.Name, string(t.Category), string(t.Status),
		t.EstimatedCost, t.ActualCost,
		t.Contractor, t.Notes,
		formatNullableTime(t.DueDate),
		t.UpdatedAt.UTC().Format(time.RFC3339),
		t.ID,
	)
	if err != nil {
		return fmt.Errorf("tasks.Update: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("tasks.Update rows affected: %w", err)
	}
	if n == 0 {
		return domain.ErrNotFound
	}
	return nil
}

func (r *taskRepository) Delete(ctx context.Context, id string) error {
	const q = `DELETE FROM tasks WHERE id=?`
	res, err := r.db.ExecContext(ctx, q, id)
	if err != nil {
		return fmt.Errorf("tasks.Delete: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("tasks.Delete rows affected: %w", err)
	}
	if n == 0 {
		return domain.ErrNotFound
	}
	return nil
}

// ---- helpers ----------------------------------------------------------------

func scanTask(s scanner) (domain.RenovationTask, error) {
	var t domain.RenovationTask
	var category, status, createdAt, updatedAt string
	var actualCost sql.NullFloat64
	var dueDate sql.NullString

	err := s.Scan(
		&t.ID, &t.RoomID, &t.Name,
		&category, &status,
		&t.EstimatedCost, &actualCost,
		&t.Contractor, &t.Notes,
		&dueDate, &createdAt, &updatedAt,
	)
	if err != nil {
		return t, err
	}

	t.Category = domain.TaskCategory(category)
	t.Status = domain.TaskStatus(status)

	if actualCost.Valid {
		v := actualCost.Float64
		t.ActualCost = &v
	}
	if dueDate.Valid && dueDate.String != "" {
		parsed, err := time.Parse(time.RFC3339, dueDate.String)
		if err == nil {
			t.DueDate = &parsed
		}
	}
	t.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
	t.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
	return t, nil
}

func formatNullableTime(t *time.Time) *string {
	if t == nil {
		return nil
	}
	s := t.UTC().Format(time.RFC3339)
	return &s
}
