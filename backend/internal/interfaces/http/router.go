package http

import (
	"net/http"
	"strings"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/newarch/renovation-planner/internal/application"
)

// NewRouter builds and returns the chi router with all routes mounted.
// openapiSpec is the raw bytes of the OpenAPI YAML file, embedded by the caller.
func NewRouter(
	projectSvc *application.ProjectService,
	roomSvc *application.RoomService,
	taskSvc *application.TaskService,
	openapiSpec []byte,
) http.Handler {
	r := chi.NewRouter()

	// Global middleware — order matters: RequestID first so logger can read it
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(requestLogger)   // structured slog JSON logger
	r.Use(middleware.Recoverer)
	r.Use(corsMiddleware)

	// Health check
	r.Get("/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})

	// OpenAPI spec — served as raw YAML
	r.Get("/openapi.yaml", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/yaml")
		_, _ = w.Write(openapiSpec)
	})

	// Swagger UI — served via unpkg CDN; no extra binary required
	r.Get("/docs", func(w http.ResponseWriter, r *http.Request) {
		// Redirect /docs → /docs/ so relative paths resolve correctly
		if !strings.HasSuffix(r.URL.Path, "/") {
			http.Redirect(w, r, r.URL.Path+"/", http.StatusMovedPermanently)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write(swaggerUIHTML)
	})
	r.Get("/docs/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write(swaggerUIHTML)
	})

	// API v1
	ph := NewProjectHandler(projectSvc)
	rh := NewRoomHandler(roomSvc)
	th := NewTaskHandler(taskSvc)

	r.Route("/api/v1", func(r chi.Router) {
		// Projects
		r.Get("/projects", ph.List)
		r.Post("/projects", ph.Create)
		r.Get("/projects/{id}", ph.Get)
		r.Put("/projects/{id}", ph.Update)
		r.Delete("/projects/{id}", ph.Delete)

		// Rooms (nested under project for create/list, top-level for get/update/delete)
		r.Get("/projects/{projectID}/rooms", rh.ListByProject)
		r.Post("/projects/{projectID}/rooms", rh.Create)
		r.Get("/rooms/{id}", rh.Get)
		r.Put("/rooms/{id}", rh.Update)
		r.Delete("/rooms/{id}", rh.Delete)

		// Tasks (nested under room for create/list, top-level for get/update/delete)
		r.Get("/rooms/{roomID}/tasks", th.ListByRoom)
		r.Post("/rooms/{roomID}/tasks", th.Create)
		r.Get("/tasks/{id}", th.Get)
		r.Put("/tasks/{id}", th.Update)
		r.Delete("/tasks/{id}", th.Delete)
	})

	return r
}

// swaggerUIHTML is a minimal Swagger UI page that loads the spec from /openapi.yaml.
// Uses unpkg CDN — no extra packages or binary generation required.
var swaggerUIHTML = []byte(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Renovation Planner API Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
  SwaggerUIBundle({
    url: "/openapi.yaml",
    dom_id: "#swagger-ui",
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
    layout: "BaseLayout",
    deepLinking: true,
    tryItOutEnabled: true,
  });
</script>
</body>
</html>`)
