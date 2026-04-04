package main

import (
	_ "embed"
	"fmt"
	"log"
	"log/slog"
	"net/http"
	"os"

	"github.com/newarch/renovation-planner/internal/application"
	httphandler "github.com/newarch/renovation-planner/internal/interfaces/http"
	"github.com/newarch/renovation-planner/internal/infrastructure/sqlite"
)

//go:embed docs/openapi.yaml
var openapiSpec []byte

func main() {
	// Use JSON structured logging throughout — works well with Docker log drivers.
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})))

	dbPath := getenv("DB_PATH", "./data/renovation.db")
	port := getenv("PORT", "8080")

	// ── Infrastructure ────────────────────────────────────────────────────────
	db, err := sqlite.NewDB(dbPath)
	if err != nil {
		log.Fatalf("failed to open database at %s: %v", dbPath, err)
	}
	defer db.Close()

	projectRepo := sqlite.NewProjectRepository(db)
	roomRepo    := sqlite.NewRoomRepository(db)
	taskRepo    := sqlite.NewTaskRepository(db)

	// ── Application ───────────────────────────────────────────────────────────
	projectSvc := application.NewProjectService(projectRepo)
	roomSvc    := application.NewRoomService(roomRepo, projectRepo)
	taskSvc    := application.NewTaskService(taskRepo, roomRepo)

	// ── HTTP ──────────────────────────────────────────────────────────────────
	router := httphandler.NewRouter(projectSvc, roomSvc, taskSvc, openapiSpec)

	addr := fmt.Sprintf(":%s", port)
	log.Printf("renovation-planner API listening on %s (db: %s)", addr, dbPath)
	if err := http.ListenAndServe(addr, router); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
