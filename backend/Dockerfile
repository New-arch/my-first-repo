# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM golang:1.22-alpine AS builder

# libsqlite3-dev + gcc required for the CGO SQLite driver
RUN apk add --no-cache gcc musl-dev sqlite-dev

WORKDIR /app

# Download dependencies first (layer-cached separately from source changes).
COPY go.mod go.sum ./
RUN go mod download

# Copy source and build.
# CGO_ENABLED=1 required for the inline CGO SQLite3 driver.
COPY . .
RUN CGO_ENABLED=1 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-s -w" -o /renovation-api .

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
# Use a minimal Alpine image (not distroless) so shell access is possible for
# debugging. Switch to distroless/static for production hardening.
FROM alpine:3.19

# ca-certificates for HTTPS calls; sqlite-libs for the CGO SQLite3 driver at runtime
RUN apk add --no-cache ca-certificates tzdata sqlite-libs

WORKDIR /app
COPY --from=builder /renovation-api .

# Copy the OpenAPI spec so it is available inside the container at runtime
# (the embed directive bakes it into the binary, but keeping it explicit is
# useful for documentation tooling mounted against the container).
COPY docs/ ./docs/

RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8080

ENV DB_PATH=/data/renovation.db
ENV PORT=8080

ENTRYPOINT ["./renovation-api"]
