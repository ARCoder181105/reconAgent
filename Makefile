.PHONY: help install test lint gen score demo demo-multi clean data web web-build web-install

 SHELL := /bin/bash
PY := .venv/bin/python
PIP := .venv/bin/pip
NPM := npm --prefix frontend

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Create venv and install requirements
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

test: ## Run the full backend test suite
	$(PY) -m pytest backend/tests/ -q

test-v: ## Run tests with verbose output
	$(PY) -m pytest backend/tests/ -v

lint: ## Lint check (pyflakes-style unused imports)
	$(PY) -m flake8 backend/app backend/eval backend/tests || echo "flake8 not installed (pip install flake8)"

gen: ## Generate synthetic data (settlements.csv, bank_statement.csv, answer_key.json)
	$(PY) -c "from backend.app.data_generator.generator import generate_to_disk; generate_to_disk()"
	@echo "wrote data to backend/data/"

score: ## Generate + reconcile + score against hidden answer key (seed 42)
	$(PY) -m backend.eval.run_score --seed 42

score-seed: ## Score with a custom seed: make score-seed SEED=7
	$(PY) -m backend.eval.run_score --seed $(SEED)

demo: ## One-command demo: generate + reconcile + score + headline numbers (seed 42)
	$(PY) scripts/demo.py --seed 42

demo-multi: ## Multi-seed robustness: demo over seeds 1..N (make demo-multi N=10)
	$(PY) scripts/demo.py --multi $(or $(N),10)

dev: ## Run the FastAPI server (Iteration 07 target: backend/app/main.py)
	$(PY) -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

web-install: ## Install frontend dependencies (npm)
	$(NPM) install

web: ## Run the Vite dev server (Iteration 09 dashboard)
	$(NPM) run dev

web-build: ## Type-check + production-build the frontend
	$(NPM) run build

web-lint: ## Lint the frontend
	$(NPM) run lint

clean: ## Remove venv + generated data + caches
	rm -rf .venv .pytest_cache backend/data/* backend/**/__pycache__
	@echo "cleaned"

data: ## Show what generated data files exist
	@ls -la backend/data/
