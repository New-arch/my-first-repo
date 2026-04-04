package domain

import (
	"errors"
	"time"
)

// Room represents a single room within a renovation project.
type Room struct {
	ID        string
	ProjectID string
	Name      string
	AreaSqm   float64
	Tasks     []RenovationTask // populated by application layer when doing eager loads
	CreatedAt time.Time
	UpdatedAt time.Time
}

// Validate checks that the room satisfies basic business rules.
func (r *Room) Validate() error {
	if r.Name == "" {
		return errors.New("room name is required")
	}
	if r.AreaSqm < 0 {
		return errors.New("area cannot be negative")
	}
	return nil
}

// EstimatedCost sums estimated costs of all tasks (requires Tasks to be loaded).
func (r *Room) EstimatedCost() float64 {
	var total float64
	for _, t := range r.Tasks {
		total += t.EstimatedCost
	}
	return total
}

// ActualCost sums actual costs of tasks that have been recorded.
func (r *Room) ActualCost() float64 {
	var total float64
	for _, t := range r.Tasks {
		if t.ActualCost != nil {
			total += *t.ActualCost
		}
	}
	return total
}

// CompletionPercent returns the percentage of tasks marked Done (0–100).
func (r *Room) CompletionPercent() float64 {
	if len(r.Tasks) == 0 {
		return 0
	}
	var done int
	for _, t := range r.Tasks {
		if t.Status == TaskStatusDone {
			done++
		}
	}
	return float64(done) / float64(len(r.Tasks)) * 100
}
