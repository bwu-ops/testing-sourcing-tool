SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help setup verify_setup dev dev_stop llm_local_setup llm_local_start llm_local_stop test lint typecheck security fmt build deploy

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install deps, run codegen, apply migrations
	./scripts/setup.sh

verify_setup: ## Check required tools and versions
	./scripts/verify_setup.sh

dev: ## Start web app and API (keeps running)
	./scripts/dev.sh

dev_stop: ## Stop leftover local dev processes
	./scripts/dev_stop.sh

llm_local_setup: ## One-time local Qwen download (~4.5 GB)
	./scripts/llm_local_setup.sh

llm_local_start: ## Start local LLM runtime
	./scripts/llm_local_start.sh

llm_local_stop: ## Stop local LLM runtime
	./scripts/llm_local_stop.sh

test: ## Run backend and frontend tests
	cd apps/api && uv run pytest
	cd apps/web && yarn test

lint: ## Run backend and frontend linters
	cd apps/api && uv run ruff check src tests
	cd apps/api && uv run ruff format --check src tests
	cd apps/web && yarn lint
	cd apps/web && yarn format:check

typecheck: ## Run backend and frontend type checks
	cd apps/api && uv run mypy src
	cd apps/web && yarn codegen:check
	cd apps/web && yarn typecheck

security: ## Run secret scan and dependency audits
	python3 ./scripts/check_secrets.py
	cd apps/api && uv run pip-audit
	cd apps/api && uv run ruff check src --select S
	cd apps/web && yarn audit --level high --groups dependencies

fmt: ## Auto-format backend and frontend code
	cd apps/api && uv run ruff format src tests
	cd apps/web && yarn format

build: ## Build Docker image
	docker build -t scaffold-app .

deploy: ## Print deploy env and show deploy command
	./scripts/gcp_print_env.sh
	@echo "Deploy command template:"
	@echo "gcloud run deploy scaffold-app --source . --region us-central1 --allow-unauthenticated"
