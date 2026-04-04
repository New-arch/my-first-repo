package http

import (
	"time"

	"github.com/newarch/renovation-planner/internal/domain"
)

// ---- Request bodies --------------------------------------------------------

// ProjectRequest is the JSON body for create and update project endpoints.
type ProjectRequest struct {
	Name        string  `json:"name"`
	Address     string  `json:"address"`
	TotalBudget float64 `json:"total_budget"`
	StartDate   string  `json:"start_date"`  // ISO8601 / RFC3339
	TargetDate  string  `json:"target_date"` // ISO8601 / RFC3339
	Status      string  `json:"status"`
}

// RoomRequest is the JSON body for create and update room endpoints.
type RoomRequest struct {
	Name    string  `json:"name"`
	AreaSqm float64 `json:"area_sqm"`
}

// TaskRequest is the JSON body for create and update task endpoints.
type TaskRequest struct {
	Name          string   `json:"name"`
	Category      string   `json:"category"`
	Status        string   `json:"status"`
	EstimatedCost float64  `json:"estimated_cost"`
	ActualCost    *float64 `json:"actual_cost,omitempty"`
	Contractor    string   `json:"contractor"`
	Notes         string   `json:"notes"`
	DueDate       *string  `json:"due_date,omitempty"` // ISO8601
}

// ---- Response bodies -------------------------------------------------------

// ProjectResponse is returned for all project endpoints.
type ProjectResponse struct {
	ID          string         `json:"id"`
	Name        string         `json:"name"`
	Address     string         `json:"address"`
	TotalBudget float64        `json:"total_budget"`
	StartDate   string         `json:"start_date"`
	TargetDate  string         `json:"target_date"`
	Status      string         `json:"status"`
	CreatedAt   string         `json:"created_at"`
	UpdatedAt   string         `json:"updated_at"`
	Rooms       []RoomResponse `json:"rooms,omitempty"`
}

// RoomResponse is returned for all room endpoints.
type RoomResponse struct {
	ID        string         `json:"id"`
	ProjectID string         `json:"project_id"`
	Name      string         `json:"name"`
	AreaSqm   float64        `json:"area_sqm"`
	CreatedAt string         `json:"created_at"`
	UpdatedAt string         `json:"updated_at"`
	Tasks     []TaskResponse `json:"tasks,omitempty"`
}

// TaskResponse is returned for all task endpoints.
type TaskResponse struct {
	ID            string   `json:"id"`
	RoomID        string   `json:"room_id"`
	Name          string   `json:"name"`
	Category      string   `json:"category"`
	Status        string   `json:"status"`
	EstimatedCost float64  `json:"estimated_cost"`
	ActualCost    *float64 `json:"actual_cost,omitempty"`
	Contractor    string   `json:"contractor"`
	Notes         string   `json:"notes"`
	DueDate       *string  `json:"due_date,omitempty"`
	CreatedAt     string   `json:"created_at"`
	UpdatedAt     string   `json:"updated_at"`
}

// ErrorResponse wraps error messages for all error responses.
type ErrorResponse struct {
	Error string `json:"error"`
}

// ---- Mappers ---------------------------------------------------------------

func projectToResponse(p *domain.Project) ProjectResponse {
	resp := ProjectResponse{
		ID:          p.ID,
		Name:        p.Name,
		Address:     p.Address,
		TotalBudget: p.TotalBudget,
		StartDate:   p.StartDate.UTC().Format(time.RFC3339),
		TargetDate:  p.TargetDate.UTC().Format(time.RFC3339),
		Status:      string(p.Status),
		CreatedAt:   p.CreatedAt.UTC().Format(time.RFC3339),
		UpdatedAt:   p.UpdatedAt.UTC().Format(time.RFC3339),
	}
	for i := range p.Rooms {
		resp.Rooms = append(resp.Rooms, roomToResponse(&p.Rooms[i]))
	}
	return resp
}

func roomToResponse(r *domain.Room) RoomResponse {
	resp := RoomResponse{
		ID:        r.ID,
		ProjectID: r.ProjectID,
		Name:      r.Name,
		AreaSqm:   r.AreaSqm,
		CreatedAt: r.CreatedAt.UTC().Format(time.RFC3339),
		UpdatedAt: r.UpdatedAt.UTC().Format(time.RFC3339),
	}
	for i := range r.Tasks {
		resp.Tasks = append(resp.Tasks, taskToResponse(&r.Tasks[i]))
	}
	return resp
}

func taskToResponse(t *domain.RenovationTask) TaskResponse {
	resp := TaskResponse{
		ID:            t.ID,
		RoomID:        t.RoomID,
		Name:          t.Name,
		Category:      string(t.Category),
		Status:        string(t.Status),
		EstimatedCost: t.EstimatedCost,
		ActualCost:    t.ActualCost,
		Contractor:    t.Contractor,
		Notes:         t.Notes,
		CreatedAt:     t.CreatedAt.UTC().Format(time.RFC3339),
		UpdatedAt:     t.UpdatedAt.UTC().Format(time.RFC3339),
	}
	if t.DueDate != nil {
		s := t.DueDate.UTC().Format(time.RFC3339)
		resp.DueDate = &s
	}
	return resp
}
