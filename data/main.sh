#!/usr/bin/env bash
set -euo pipefail

# LocalCloud development bootstrap script

APP_NAME="localcloud"
BACKEND_DIR="./backend"
FRONTEND_DIR="./frontend"
VENV_DIR="$BACKEND_DIR/.venv"

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "[$(date '+%H:%M:%S')] ✓ $*"; }
err()  { echo "[$(date '+%H:%M:%S')] ✗ $*" >&2; exit 1; }

check_deps() {
    local missing=()
    for cmd in python3 node npm docker; do
        command -v "$cmd" &>/dev/null || missing+=("$cmd")
    done
    [[ ${#missing[@]} -eq 0 ]] || err "Missing: ${missing[*]}"
    ok "All dependencies found"
}

setup_venv() {
    log "Setting up Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --quiet -e "$BACKEND_DIR"
    ok "Backend dependencies installed"
}

start_services() {
    log "Starting MinIO and PostgreSQL via Docker Compose..."
    docker compose up -d minio postgres
    sleep 3
    ok "Services started"
}

start_backend() {
    log "Starting FastAPI backend..."
    source "$VENV_DIR/bin/activate"
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    ok "Backend PID=$BACKEND_PID"
}

start_frontend() {
    log "Starting Vite dev server..."
    cd "$FRONTEND_DIR"
    npm run dev &
    FRONTEND_PID=$!
    cd - >/dev/null
    ok "Frontend PID=$FRONTEND_PID"
}

cleanup() {
    log "Shutting down..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

main() {
    log "Bootstrapping $APP_NAME"
    check_deps
    setup_venv
    start_services
    start_backend
    start_frontend
    trap cleanup EXIT
    log "Ready → http://localhost:5173"
    wait
}

main "$@"
