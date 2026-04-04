package http

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/newarch/renovation-planner/internal/application"
)

// ProjectHandler handles HTTP requests for the /api/v1/projects routes.
type ProjectHandler struct {
	svc *application.ProjectService
}

// NewProjectHandler creates a ProjectHandler.
func NewProjectHandler(svc *application.ProjectService) *ProjectHandler {
	return &ProjectHandler{svc: svc}
}

// List handles GET /api/v1/projects
func (h *ProjectHandler) List(w http.ResponseWriter, r *http.Request) {
	projects, err := h.svc.ListProjects(r.Context())
	if err != nil {
		writeError(w, err)
		return
	}

	resp := make([]ProjectResponse, 0, len(projects))
	for i := range projects {
		resp = append(resp, projectToResponse(&projects[i]))
	}
	writeJSON(w, http.StatusOK, resp)
}

// Get handles GET /api/v1/projects/{id}
func (h *ProjectHandler) Get(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	project, err := h.svc.GetProject(r.Context(), id)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, projectToResponse(project))
}

// Create handles POST /api/v1/projects
func (h *ProjectHandler) Create(w http.ResponseWriter, r *http.Request) {
	var req ProjectRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid JSON body"})
		return
	}

	cmd, err := projectRequestToCommand(req)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
		return
	}

	project, err := h.svc.CreateProject(r.Context(), cmd)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, projectToResponse(project))
}

// Update handles PUT /api/v1/projects/{id}
func (h *ProjectHandler) Update(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")

	var req ProjectRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid JSON body"})
		return
	}

	cmd, err := projectRequestToCommand(req)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
		return
	}

	project, err := h.svc.UpdateProject(r.Context(), id, cmd)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, projectToResponse(project))
}

// Delete handles DELETE /api/v1/projects/{id}
func (h *ProjectHandler) Delete(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	if err := h.svc.DeleteProject(r.Context(), id); err != nil {
		writeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// ---- helpers ----------------------------------------------------------------

func projectRequestToCommand(req ProjectRequest) (application.CreateProjectCommand, error) {
	startDate, err := time.Parse(time.RFC3339, req.StartDate)
	if err != nil {
		return application.CreateProjectCommand{}, fmt.Errorf("invalid start_date: %w", err)
	}
	targetDate, err := time.Parse(time.RFC3339, req.TargetDate)
	if err != nil {
		return application.CreateProjectCommand{}, fmt.Errorf("invalid target_date: %w", err)
	}
	return application.CreateProjectCommand{
		Name:        req.Name,
		Address:     req.Address,
		TotalBudget: req.TotalBudget,
		StartDate:   startDate,
		TargetDate:  targetDate,
		Status:      req.Status,
	}, nil
}
