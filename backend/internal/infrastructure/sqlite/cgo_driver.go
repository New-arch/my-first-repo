package sqlite

// Minimal CGO-based SQLite3 driver that satisfies database/sql/driver.
// Uses the system libsqlite3 (libsqlite3-dev) — no external Go packages needed.
//
// The driver registers itself as "sqlite" via init(), so sql.Open("sqlite", path)
// just works. The Dockerfile builder stage must have libsqlite3-dev installed.

/*
#cgo LDFLAGS: -lsqlite3
#include <sqlite3.h>
#include <stdlib.h>
*/
import "C"

import (
	"database/sql"
	"database/sql/driver"
	"fmt"
	"io"
	"time"
	"unsafe"
)

func init() {
	sql.Register("sqlite", &sqliteDriver{})
}

// ── Driver ───────────────────────────────────────────────────────────────────

type sqliteDriver struct{}

func (d *sqliteDriver) Open(name string) (driver.Conn, error) {
	cname := C.CString(name)
	defer C.free(unsafe.Pointer(cname))

	var db *C.sqlite3
	if rc := C.sqlite3_open_v2(cname, &db,
		C.SQLITE_OPEN_READWRITE|C.SQLITE_OPEN_CREATE|C.SQLITE_OPEN_FULLMUTEX,
		nil,
	); rc != C.SQLITE_OK {
		msg := C.GoString(C.sqlite3_errmsg(db))
		C.sqlite3_close(db)
		return nil, fmt.Errorf("sqlite3_open: %s", msg)
	}
	// 5 second busy timeout — prevents SQLITE_BUSY errors under light concurrency.
	C.sqlite3_busy_timeout(db, 5000)
	return &sqliteConn{db: db}, nil
}

// ── Conn ─────────────────────────────────────────────────────────────────────

type sqliteConn struct {
	db *C.sqlite3
}

func (c *sqliteConn) Prepare(query string) (driver.Stmt, error) {
	cquery := C.CString(query)
	defer C.free(unsafe.Pointer(cquery))

	var stmt *C.sqlite3_stmt
	if rc := C.sqlite3_prepare_v2(c.db, cquery, -1, &stmt, nil); rc != C.SQLITE_OK {
		return nil, sqliteError(c.db)
	}
	return &sqliteStmt{db: c.db, stmt: stmt}, nil
}

func (c *sqliteConn) Close() error {
	if rc := C.sqlite3_close_v2(c.db); rc != C.SQLITE_OK {
		return sqliteError(c.db)
	}
	return nil
}

func (c *sqliteConn) Begin() (driver.Tx, error) {
	if _, err := c.execDirect("BEGIN"); err != nil {
		return nil, err
	}
	return &sqliteTx{conn: c}, nil
}

func (c *sqliteConn) execDirect(query string) (driver.Result, error) {
	stmt, err := c.Prepare(query)
	if err != nil {
		return nil, err
	}
	defer stmt.Close()
	return stmt.(*sqliteStmt).Exec(nil)
}

// ── Tx ───────────────────────────────────────────────────────────────────────

type sqliteTx struct{ conn *sqliteConn }

func (t *sqliteTx) Commit() error {
	_, err := t.conn.execDirect("COMMIT")
	return err
}

func (t *sqliteTx) Rollback() error {
	_, err := t.conn.execDirect("ROLLBACK")
	return err
}

// ── Stmt ─────────────────────────────────────────────────────────────────────

type sqliteStmt struct {
	db   *C.sqlite3
	stmt *C.sqlite3_stmt
}

func (s *sqliteStmt) Close() error {
	C.sqlite3_finalize(s.stmt)
	return nil
}

// NumInput returns -1 to let database/sql count '?' placeholders itself.
func (s *sqliteStmt) NumInput() int { return -1 }

func (s *sqliteStmt) Exec(args []driver.Value) (driver.Result, error) {
	if err := s.bind(args); err != nil {
		return nil, err
	}
	rc := C.sqlite3_step(s.stmt)
	C.sqlite3_reset(s.stmt)
	if rc != C.SQLITE_DONE && rc != C.SQLITE_ROW {
		return nil, sqliteError(s.db)
	}
	lastID := int64(C.sqlite3_last_insert_rowid(s.db))
	rowsAff := int64(C.sqlite3_changes(s.db))
	return &sqliteResult{lastID: lastID, rowsAff: rowsAff}, nil
}

func (s *sqliteStmt) Query(args []driver.Value) (driver.Rows, error) {
	if err := s.bind(args); err != nil {
		return nil, err
	}
	ncols := int(C.sqlite3_column_count(s.stmt))
	cols := make([]string, ncols)
	for i := range cols {
		cols[i] = C.GoString(C.sqlite3_column_name(s.stmt, C.int(i)))
	}
	return &sqliteRows{stmt: s, cols: cols}, nil
}

func (s *sqliteStmt) bind(args []driver.Value) error {
	C.sqlite3_reset(s.stmt)
	C.sqlite3_clear_bindings(s.stmt)
	for i, arg := range args {
		idx := C.int(i + 1)
		var rc C.int
		switch v := arg.(type) {
		case nil:
			rc = C.sqlite3_bind_null(s.stmt, idx)
		case int64:
			rc = C.sqlite3_bind_int64(s.stmt, idx, C.sqlite3_int64(v))
		case float64:
			rc = C.sqlite3_bind_double(s.stmt, idx, C.double(v))
		case bool:
			if v {
				rc = C.sqlite3_bind_int64(s.stmt, idx, 1)
			} else {
				rc = C.sqlite3_bind_int64(s.stmt, idx, 0)
			}
		case []byte:
			if len(v) == 0 {
				rc = C.sqlite3_bind_zeroblob(s.stmt, idx, 0)
			} else {
				rc = C.sqlite3_bind_blob(s.stmt, idx,
					unsafe.Pointer(&v[0]), C.int(len(v)), C.SQLITE_TRANSIENT)
			}
		case string:
			cs := C.CString(v)
			rc = C.sqlite3_bind_text(s.stmt, idx, cs, C.int(len(v)), C.SQLITE_TRANSIENT)
			C.free(unsafe.Pointer(cs))
		case time.Time:
			ts := v.UTC().Format(time.RFC3339)
			cs := C.CString(ts)
			rc = C.sqlite3_bind_text(s.stmt, idx, cs, C.int(len(ts)), C.SQLITE_TRANSIENT)
			C.free(unsafe.Pointer(cs))
		default:
			return fmt.Errorf("unsupported bind type %T at index %d", arg, i+1)
		}
		if rc != C.SQLITE_OK {
			return sqliteError(s.db)
		}
	}
	return nil
}

// ── Rows ─────────────────────────────────────────────────────────────────────

type sqliteRows struct {
	stmt *sqliteStmt
	cols []string
	done bool
}

func (r *sqliteRows) Columns() []string { return r.cols }

func (r *sqliteRows) Close() error {
	C.sqlite3_reset(r.stmt.stmt)
	return nil
}

func (r *sqliteRows) Next(dest []driver.Value) error {
	if r.done {
		return io.EOF
	}
	rc := C.sqlite3_step(r.stmt.stmt)
	if rc == C.SQLITE_DONE {
		r.done = true
		return io.EOF
	}
	if rc != C.SQLITE_ROW {
		return sqliteError(r.stmt.db)
	}
	for i := range dest {
		colType := C.sqlite3_column_type(r.stmt.stmt, C.int(i))
		switch colType {
		case C.SQLITE_INTEGER:
			dest[i] = int64(C.sqlite3_column_int64(r.stmt.stmt, C.int(i)))
		case C.SQLITE_FLOAT:
			dest[i] = float64(C.sqlite3_column_double(r.stmt.stmt, C.int(i)))
		case C.SQLITE_TEXT:
			dest[i] = C.GoString((*C.char)(unsafe.Pointer(C.sqlite3_column_text(r.stmt.stmt, C.int(i)))))
		case C.SQLITE_BLOB:
			n := int(C.sqlite3_column_bytes(r.stmt.stmt, C.int(i)))
			if n == 0 {
				dest[i] = []byte{}
			} else {
				b := make([]byte, n)
				copy(b, C.GoBytes(C.sqlite3_column_blob(r.stmt.stmt, C.int(i)), C.int(n)))
				dest[i] = b
			}
		case C.SQLITE_NULL:
			dest[i] = nil
		}
	}
	return nil
}

// ── Result ───────────────────────────────────────────────────────────────────

type sqliteResult struct {
	lastID  int64
	rowsAff int64
}

func (r *sqliteResult) LastInsertId() (int64, error) { return r.lastID, nil }
func (r *sqliteResult) RowsAffected() (int64, error) { return r.rowsAff, nil }

// ── Helper ───────────────────────────────────────────────────────────────────

func sqliteError(db *C.sqlite3) error {
	return fmt.Errorf("sqlite3: %s (code %d)",
		C.GoString(C.sqlite3_errmsg(db)),
		C.sqlite3_errcode(db))
}
