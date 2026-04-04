package domain

import "errors"

// Sentinel errors used across all layers.
// Infrastructure repositories must wrap their not-found conditions with these.
var (
	ErrNotFound       = errors.New("not found")
	ErrAlreadyExists  = errors.New("already exists")
	ErrInvalidInput   = errors.New("invalid input")
)
