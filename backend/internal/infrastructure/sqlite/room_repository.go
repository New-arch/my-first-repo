package sqlite

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/newarch/renovation-planner/internal/domain"
)

type roomRepository struct {
	db *DB
}

// NewRoomRepository returns a SQLite-backed RoomRepository.
func NewRoomRepository(db *DB) domain.RoomRepository {
	return &roomRepository{db: db}
}

func (r *roomRepository) FindByProjectID(ctx context.Context, projectID string) ([]domain.Room, error) {
	const q = `SELECT id, project_id, name, area_sqm, created_at, updated_at
	           FROM rooms WHERE project_id = ? ORDER BY name`

	rows, err := r.db.QueryContext(ctx, q, projectID)
	if err != nil {
		return nil, fmt.Errorf("rooms.FindByProjectID query: %w", err)
	}
	defer rows.Close()

	var rooms []domain.Room
	for rows.Next() {
		rm, err := scanRoom(rows)
		if err != nil {
			return nil, err
		}
		rooms = append(rooms, rm)
	}
	return rooms, rows.Err()
}

func (r *roomRepository) FindByID(ctx context.Context, id string) (*domain.Room, error) {
	const q = `SELECT id, project_id, name, area_sqm, created_at, updated_at
	           FROM rooms WHERE id = ?`

	row := r.db.QueryRowContext(ctx, q, id)
	rm, err := scanRoom(row)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, domain.ErrNotFound
		}
		return nil, fmt.Errorf("rooms.FindByID: %w", err)
	}
	return &rm, nil
}

func (r *roomRepository) FindByIDWithTasks(ctx context.Context, id string) (*domain.Room, error) {
	rm, err := r.FindByID(ctx, id)
	if err != nil {
		return nil, err
	}

	taskRepo := &taskRepository{db: r.db}
	tasks, err := taskRepo.FindByRoomID(ctx, id)
	if err != nil {
		return nil, err
	}
	rm.Tasks = tasks
	return rm, nil
}

func (r *roomRepository) Create(ctx context.Context, rm *domain.Room) error {
	const q = `INSERT INTO rooms (id, project_id, name, area_sqm, created_at, updated_at)
	           VALUES (?, ?, ?, ?, ?, ?)`

	_, err := r.db.ExecContext(ctx, q,
		rm.ID, rm.ProjectID, rm.Name, rm.AreaSqm,
		rm.CreatedAt.UTC().Format(time.RFC3339),
		rm.UpdatedAt.UTC().Format(time.RFC3339),
	)
	if err != nil {
		return fmt.Errorf("rooms.Create: %w", err)
	}
	return nil
}

func (r *roomRepository) Update(ctx context.Context, rm *domain.Room) error {
	const q = `UPDATE rooms SET name=?, area_sqm=?, updated_at=? WHERE id=?`

	res, err := r.db.ExecContext(ctx, q,
		rm.Name, rm.AreaSqm,
		rm.UpdatedAt.UTC().Format(time.RFC3339),
		rm.ID,
	)
	if err != nil {
		return fmt.Errorf("rooms.Update: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rooms.Update rows affected: %w", err)
	}
	if n == 0 {
		return domain.ErrNotFound
	}
	return nil
}

func (r *roomRepository) Delete(ctx context.Context, id string) error {
	const q = `DELETE FROM rooms WHERE id=?`
	res, err := r.db.ExecContext(ctx, q, id)
	if err != nil {
		return fmt.Errorf("rooms.Delete: %w", err)
	}
	n, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("rooms.Delete rows affected: %w", err)
	}
	if n == 0 {
		return domain.ErrNotFound
	}
	return nil
}

func scanRoom(s scanner) (domain.Room, error) {
	var rm domain.Room
	var createdAt, updatedAt string

	err := s.Scan(&rm.ID, &rm.ProjectID, &rm.Name, &rm.AreaSqm, &createdAt, &updatedAt)
	if err != nil {
		return rm, err
	}
	rm.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
	rm.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
	return rm, nil
}
