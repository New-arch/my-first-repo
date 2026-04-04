package http

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/newarch/renovation-planner/internal/application"
)

// TaskHandler handles HTTP requests for task routes.
type TaskHandler struct {
	svc *application.TaskService
}

// NewTaskHandler creates a TaskHandler.
func NewTaskHandler(svc *application.TaskService) *TaskHandler {
	return &TaskHandler{svc: svc}
}

// ListByRoom handles GET /api/v1/rooms/{roomID}/tasks
func (h *TaskHandler) ListByRoom(w http.ResponseWriter, r *http.Request) {
	roomID := chi.URLParam(r, "roomID")
	tasks, err := h.svc.ListTasks(r.Context(), roomID)
	if err != nil {
		writeError(w, err)
		return
	}

	resp := make([]TaskResponse, 0, len(tasks))
	for i := range tasks {
		resp = append(resp, taskToResponse(&tasks[i]))
	}
	writeJSON(w, http.StatusOK, resp)
}

// Get handles GET /api/v1/tasks/{id}
func (h *TaskHandler) Get(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	task, err := h.svc.GetTask(r.Context(), id)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, taskToResponse(task))
}

// Create handles POST /api/v1/rooms/{roomID}/tasks
func (h *TaskHandler) Create(w http.ResponseWriter, r *http.Request) {
	roomID := chi.URLParam(r, "roomID")

	var req TaskRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid JSON body"})
		return
	}

	cmd, err := taskRequestToCommand(req)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
		return
	}

	task, err := h.svc.CreateTask(r.Context(), roomID, cmd)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, taskToResponse(task))
}

// Update handles PUT /api/v1/tasks/{id}
func (h *TaskHandler) Update(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")

	var req TaskRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid JSON body"})
		return
	}

	cmd, err := taskRequestToCommand(req)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
		return
	}

	task, err := h.svc.UpdateTask(r.Context(), id, cmd)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, taskToResponse(task))
}

// Delete handles DELETE /api/v1/tasks/{id}
func (h *TaskHandler) Delete(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	if err := h.svc.DeleteTask(r.Context(), id); err != nil {
		writeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// ---- helpers ----------------------------------------------------------------

func taskRequestToCommand(req TaskRequest) (application.CreateTaskCommand, error) {
	cmd := application.CreateTaskCommand{
		Name:          req.Name,
		Category:      req.Category,
		Status:        req.Status,
		EstimatedCost: req.EstimatedCost,
		ActualCost:    req.ActualCost,
		Contractor:    req.Contractor,
		Notes:         req.Notes,
	}
	if req.DueDate != nil && *req.DueDate != "" {
		t, err := time.Parse(time.RFC3339, *req.DueDate)
		if err != nil {
			return cmd, fmt.Errorf("invalid due_date: %w", err)
		}
		cmd.DueDate = &t
	}
	return cmd, nil
}
