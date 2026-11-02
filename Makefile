.DEFAULT_GOAL := help
.PHONY: help build test lint run docs clean

help: ## List available targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "%-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build the wheel and sdist into dist/
	uv build

test: ## Run the test suite
	uv run pytest -q

lint: ## Format check, lint and type check, the same commands CI runs
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy

run: ## Run the command line tool
	uv run bbfmodels

docs: ## Build the documentation site strictly
	uv run --with-requirements requirements.txt --no-project python -m unittest discover -s hooks
	uv run --with-requirements requirements.txt --no-project mkdocs build --strict

clean: ## Remove build artifacts
	rm -rf dist build site .venv .pytest_cache .mypy_cache .ruff_cache
