package sqlite

import (
	"database/sql"
	"fmt"
	// cgo_driver.go in this package registers the "sqlite" driver via init()
)

// DB wraps sql.DB and owns the schema migration.
type DB struct {
	*sql.DB
}

// NewDB opens (or creates) the SQLite database at path and runs migrations.
func NewDB(path string) (*DB, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite db: %w", err)
	}

	// Verify the connection is actually usable.
	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("ping sqlite db: %w", err)
	}

	// SQLite does not support concurrent writers; cap the pool to 1.
	// Foreign-key enforcement is applied in migrate() which runs immediately
	// after open — safe because SetMaxOpenConns(1) means a single connection.
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	wrapped := &DB{db}
	if err := wrapped.migrate(); err != nil {
		return nil, fmt.Errorf("migrate: %w", err)
	}
	return wrapped, nil
}

// migrate creates all tables if they do not yet exist.
// It also enables foreign-key enforcement for the current connection.
func (db *DB) migrate() error {
	// Enable FK enforcement — must be done per connection.
	if _, err := db.Exec("PRAGMA foreign_keys = ON"); err != nil {
		return fmt.Errorf("enable foreign keys: %w", err)
	}

	// Use WAL mode for better read concurrency with the single writer constraint.
	if _, err := db.Exec("PRAGMA journal_mode = WAL"); err != nil {
		return fmt.Errorf("enable WAL: %w", err)
	}

	schema := `
	CREATE TABLE IF NOT EXISTS projects (
		id           TEXT PRIMARY KEY,
		name         TEXT NOT NULL,
		address      TEXT NOT NULL DEFAULT '',
		total_budget REAL NOT NULL DEFAULT 0,
		start_date   TEXT NOT NULL,
		target_date  TEXT NOT NULL,
		status       TEXT NOT NULL DEFAULT 'Planning',
		created_at   TEXT NOT NULL,
		updated_at   TEXT NOT NULL
	);

	CREATE TABLE IF NOT EXISTS rooms (
		id         TEXT PRIMARY KEY,
		project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
		name       TEXT NOT NULL,
		area_sqm   REAL NOT NULL DEFAULT 0,
		created_at TEXT NOT NULL,
		updated_at TEXT NOT NULL
	);

	CREATE TABLE IF NOT EXISTS tasks (
		id             TEXT PRIMARY KEY,
		room_id        TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
		name           TEXT NOT NULL,
		category       TEXT NOT NULL DEFAULT 'Other',
		status         TEXT NOT NULL DEFAULT 'Planned',
		estimated_cost REAL NOT NULL DEFAULT 0,
		actual_cost    REAL,
		contractor     TEXT NOT NULL DEFAULT '',
		notes          TEXT NOT NULL DEFAULT '',
		due_date       TEXT,
		created_at     TEXT NOT NULL,
		updated_at     TEXT NOT NULL
	);

	CREATE INDEX IF NOT EXISTS idx_rooms_project_id ON rooms(project_id);
	CREATE INDEX IF NOT EXISTS idx_tasks_room_id    ON tasks(room_id);
	`

	if _, err := db.Exec(schema); err != nil {
		return fmt.Errorf("create schema: %w", err)
	}
	return nil
}
