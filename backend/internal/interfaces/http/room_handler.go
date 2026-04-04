package http

import (
	"encoding/json"
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/newarch/renovation-planner/internal/application"
)

// RoomHandler handles HTTP requests for room routes.
type RoomHandler struct {
	svc *application.RoomService
}

// NewRoomHandler creates a RoomHandler.
func NewRoomHandler(svc *application.RoomService) *RoomHandler {
	return &RoomHandler{svc: svc}
}

// ListByProject handles GET /api/v1/projects/{projectID}/rooms
func (h *RoomHandler) ListByProject(w http.ResponseWriter, r *http.Request) {
	projectID := chi.URLParam(r, "projectID")
	rooms, err := h.svc.ListRooms(r.Context(), projectID)
	if err != nil {
		writeError(w, err)
		return
	}

	resp := make([]RoomResponse, 0, len(rooms))
	for i := range rooms {
		resp = append(resp, roomToResponse(&rooms[i]))
	}
	writeJSON(w, http.StatusOK, resp)
}

// Get handles GET /api/v1/rooms/{id}
func (h *RoomHandler) Get(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	room, err := h.svc.GetRoom(r.Context(), id)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, roomToResponse(room))
}

// Create handles POST /api/v1/projects/{projectID}/rooms
func (h *RoomHandler) Create(w http.ResponseWriter, r *http.Request) {
	projectID := chi.URLParam(r, "projectID")

	var req RoomRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid JSON body"})
		return
	}

	room, err := h.svc.CreateRoom(r.Context(), projectID, application.CreateRoomCommand{
		Name:    req.Name,
		AreaSqm: req.AreaSqm,
	})
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, roomToResponse(room))
}

// Update handles PUT /api/v1/rooms/{id}
func (h *RoomHandler) Update(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")

	var req RoomRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "invalid JSON body"})
		return
	}

	room, err := h.svc.UpdateRoom(r.Context(), id, application.UpdateRoomCommand{
		Name:    req.Name,
		AreaSqm: req.AreaSqm,
	})
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, roomToResponse(room))
}

// Delete handles DELETE /api/v1/rooms/{id}
func (h *RoomHandler) Delete(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	if err := h.svc.DeleteRoom(r.Context(), id); err != nil {
		writeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
