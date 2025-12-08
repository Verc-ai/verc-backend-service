.PHONY: help install test lint format typecheck run migrate clean docker-build docker-run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements-dev.txt

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=apps --cov-report=html --cov-report=term

lint: ## Run linters
	ruff check .
	mypy .

format: ## Format code
	black .

format-check: ## Check code formatting
	black --check .

typecheck: ## Run type checker
	mypy .

run: ## Run development server on port 4000
	python manage.py runserver 0.0.0.0:4000

run-local: ## Run using the local script
	./run-local.sh

migrate: ## Run migrations
	python manage.py migrate

makemigrations: ## Create migrations
	python manage.py makemigrations

shell: ## Open Django shell
	python manage.py shell

clean: ## Clean generated files
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

docker-build: ## Build Docker image
	docker build -t verc-backend:latest .

docker-run: ## Run Docker container
	docker run -p 8080:8080 --env-file .env verc-backend:latest

