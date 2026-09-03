.PHONY: help install test lint gen score clean data

SHELL := /bin/bash
PY := .venv/bin/python
PIP := .venv/bin/pip

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

dev: ## Run the FastAPI server (Iteration 07 target: backend/app/main.py)
	$(PY) -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

clean: ## Remove venv + generated data + caches
	rm -rf .venv .pytest_cache backend/data/* backend/**/__pycache__
	@echo "cleaned"

data: ## Show what generated data files exist
	@ls -la backend/data/
