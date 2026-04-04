package domain

import (
	"errors"
	"time"
)

// TaskStatus mirrors the Swift TaskStatus enum raw values.
type TaskStatus string

const (
	TaskStatusPlanned    TaskStatus = "Planned"
	TaskStatusInProgress TaskStatus = "In Progress"
	TaskStatusBlocked    TaskStatus = "Blocked"
	TaskStatusDone       TaskStatus = "Done"
)

// TaskCategory mirrors the Swift TaskCategory enum raw values.
type TaskCategory string

const (
	TaskCategoryElectrical TaskCategory = "Electrical"
	TaskCategoryPlumbing   TaskCategory = "Plumbing"
	TaskCategoryTiling     TaskCategory = "Tiling"
	TaskCategoryPainting   TaskCategory = "Painting"
	TaskCategoryFlooring   TaskCategory = "Flooring"
	TaskCategoryCarpentry  TaskCategory = "Carpentry"
	TaskCategoryStructural TaskCategory = "Structural"
	TaskCategoryOther      TaskCategory = "Other"
)

// RenovationTask represents a single task within a room.
type RenovationTask struct {
	ID            string
	RoomID        string
	Name          string
	Category      TaskCategory
	Status        TaskStatus
	EstimatedCost float64
	ActualCost    *float64   // nil until recorded
	Contractor    string
	Notes         string
	DueDate       *time.Time // nil if not set
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

// Validate checks that the task satisfies basic business rules.
func (t *RenovationTask) Validate() error {
	if t.Name == "" {
		return errors.New("task name is required")
	}
	if t.EstimatedCost < 0 {
		return errors.New("estimated cost cannot be negative")
	}
	if t.ActualCost != nil && *t.ActualCost < 0 {
		return errors.New("actual cost cannot be negative")
	}
	return nil
}

// CostDelta returns the difference between actual and estimated cost.
// Returns nil if actual cost has not been recorded yet.
func (t *RenovationTask) CostDelta() *float64 {
	if t.ActualCost == nil {
		return nil
	}
	delta := *t.ActualCost - t.EstimatedCost
	return &delta
}
