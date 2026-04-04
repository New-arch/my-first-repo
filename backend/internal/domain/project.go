package domain

import (
	"errors"
	"time"
)

// ProjectStatus mirrors the Swift ProjectStatus enum raw values.
type ProjectStatus string

const (
	ProjectStatusPlanning ProjectStatus = "Planning"
	ProjectStatusActive   ProjectStatus = "Active"
	ProjectStatusOnHold   ProjectStatus = "On Hold"
	ProjectStatusComplete ProjectStatus = "Complete"
)

// Project is the aggregate root for a renovation project.
// It contains no infrastructure imports — pure domain logic only.
type Project struct {
	ID          string
	Name        string
	Address     string
	TotalBudget float64
	StartDate   time.Time
	TargetDate  time.Time
	Status      ProjectStatus
	Rooms       []Room // populated by application layer when doing eager loads
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

// Validate checks that the project satisfies basic business rules.
func (p *Project) Validate() error {
	if p.Name == "" {
		return errors.New("project name is required")
	}
	if !p.TargetDate.IsZero() && !p.StartDate.IsZero() && p.TargetDate.Before(p.StartDate) {
		return errors.New("target date must be on or after start date")
	}
	if p.TotalBudget < 0 {
		return errors.New("total budget cannot be negative")
	}
	return nil
}

// TotalEstimatedCost sums estimated costs across all rooms (requires Rooms to be loaded).
func (p *Project) TotalEstimatedCost() float64 {
	var total float64
	for _, r := range p.Rooms {
		total += r.EstimatedCost()
	}
	return total
}

// TotalActualCost sums actual costs across all rooms (requires Rooms to be loaded).
func (p *Project) TotalActualCost() float64 {
	var total float64
	for _, r := range p.Rooms {
		total += r.ActualCost()
	}
	return total
}

// BudgetVariance returns the amount of budget remaining (negative = over budget).
func (p *Project) BudgetVariance() float64 {
	return p.TotalBudget - p.TotalEstimatedCost()
}

// IsOverBudget returns true when estimated cost exceeds the budget.
func (p *Project) IsOverBudget() bool {
	return p.TotalBudget > 0 && p.TotalEstimatedCost() > p.TotalBudget
}

// CompletionPercent returns the percentage of tasks marked Done (0–100).
func (p *Project) CompletionPercent() float64 {
	var total, done int
	for _, r := range p.Rooms {
		for _, t := range r.Tasks {
			total++
			if t.Status == TaskStatusDone {
				done++
			}
		}
	}
	if total == 0 {
		return 0
	}
	return float64(done) / float64(total) * 100
}
