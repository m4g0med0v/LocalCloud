.PHONY: dev build test lint fmt clean docker-up docker-down

# ── Local development ─────────────────────────────────────────────────────────

dev:            ## Start backend + frontend dev servers
	@make -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# ── Build ─────────────────────────────────────────────────────────────────────

build:          ## Build the frontend for production
	cd frontend && npm run build

# ── Tests ─────────────────────────────────────────────────────────────────────

test:           ## Run all tests
	@make -j2 test-backend test-frontend

test-backend:
	cd backend && pytest -q

test-frontend:
	cd frontend && npm run test

# ── Code quality ──────────────────────────────────────────────────────────────

lint:           ## Lint backend (ruff) and frontend (eslint)
	cd backend  && ruff check .
	cd frontend && npm run lint

fmt:            ## Format backend (ruff format) and frontend (prettier)
	cd backend  && ruff format .
	cd frontend && npm run format

# ── Docker ────────────────────────────────────────────────────────────────────

docker-up:      ## Start all services via Docker Compose
	docker compose up -d

docker-down:    ## Stop all services
	docker compose down

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:          ## Remove build artefacts
	rm -rf frontend/dist backend/.venv backend/__pycache__

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
