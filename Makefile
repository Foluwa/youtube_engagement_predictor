# YouTube Engagement Predictor
.PHONY: up down restart clean logs ps init airflow-shell mlflow-shell streamlit-shell backend-shell build rebuild help dev prod setup prune

# Default target
.DEFAULT_GOAL := help

# Environment selection (dev by default)
ENV ?= dev

# Set up Docker Compose command with appropriate files
DOCKER_COMPOSE = docker compose -f docker-compose.base.yml -f docker-compose.$(ENV).yml --env-file .env

# Services (dev vs prod)
ifeq ($(ENV),dev)
	AIRFLOW_SERVICE = airflow
	AIRFLOW_IMAGE = apache/airflow:latest
	BACKEND_PORT = 8000
else
	AIRFLOW_SERVICE = airflow-webserver
	AIRFLOW_IMAGE = apache/airflow:latest
	BACKEND_PORT = 80
endif

# Help command
help:
	@echo "Usage: make [target] [ENV=dev|prod]"
	@echo ""
	@echo "Targets:"
	@echo "  setup           Create .env file from .env.example if it doesn't exist"
	@echo "  up              Start all services in the selected environment (default: dev)"
	@echo "  down            Stop all services in the selected environment (default: dev)"
	@echo "  dev             Start all services in development environment"
	@echo "  prod            Start all services in production environment"
	@echo "  restart         Restart all services"
	@echo "  clean           Stop and remove all containers, networks, and volumes"
	@echo "  logs            Show logs from all services"
	@echo "  logs-service    Show logs from a specific service (e.g., make logs-airflow)"
	@echo "  ps              Show running services"
	@echo "  init            Initialize Airflow database and create admin user"
	@echo "  airflow-shell   Open a shell in the Airflow container"
	@echo "  mlflow-shell    Open a shell in the MLflow container"
	@echo "  streamlit-shell Open a shell in the Streamlit container"
	@echo "  backend-shell   Open a shell in the backend container"
	@echo "  build           Build all services"
	@echo "  build-fast      Build with BuildKit optimizations"
	@echo "  build-prod      Build production images with optimizations"
	@echo "  rebuild         Rebuild all services (no cache)"
	@echo "  purge           Remove all containers, networks, volumes, and images"
	@echo "  airflow-creds   Display Airflow auto-generated credentials"
	@echo "  prune           Clean up unused Docker resources"

# Setup initial environment
setup:
	@if [ ! -f .env ] && [ -f .env.example ]; then \
		cp .env.example .env; \
		echo ".env file created from .env.example. Please update with your actual values."; \
	elif [ ! -f .env ]; then \
		echo "Creating default .env file..."; \
		echo "POSTGRES_USER=airflow\nPOSTGRES_PASSWORD=airflow\nPOSTGRES_DB=airflow\n\nAIRFLOW_USER=admin\nAIRFLOW_FIRST_NAME=Admin\nAIRFLOW_LAST_NAME=User\nAIRFLOW_USER_EMAIL=admin@example.com\nAIRFLOW_PASSWORD=admin" > .env; \
		echo "Default .env file created."; \
	else \
		echo ".env file already exists."; \
	fi

# Environment-specific commands
dev:
	@$(MAKE) up ENV=dev

prod:
	@$(MAKE) up ENV=prod

# Start all services
up:
	@echo "Starting all services in $(ENV) environment..."
	@[ -f .env ] || $(MAKE) setup
	$(DOCKER_COMPOSE) up -d postgres redis
	@echo "Waiting for PostgreSQL to be ready..."
	@timeout=60; counter=0; \
	until $(DOCKER_COMPOSE) exec postgres pg_isready -U airflow 2>/dev/null || [ $$counter -eq $$timeout ]; do \
		counter=$$((counter+1)); \
		echo "PostgreSQL is unavailable - waiting ($$counter/$$timeout)..."; \
		sleep 1; \
	done; \
	if [ $$counter -eq $$timeout ]; then \
		echo "Error: PostgreSQL failed to start after $$timeout seconds"; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) up -d mlflow backend streamlit
	@sleep 3  # Wait for backend services to be ready
	$(DOCKER_COMPOSE) up -d $(AIRFLOW_SERVICE)
	@echo "Environment started. Access points:"
	@echo "  - Backend: http://localhost:$(BACKEND_PORT)"
	@echo "  - Streamlit: http://localhost:8501"
	@echo "  - MLflow: http://localhost:5001"
	@echo "  - Airflow: http://localhost:8080"

# Stop all services
down:
	@echo "Stopping all services in $(ENV) environment..."
	$(DOCKER_COMPOSE) down
	@echo "All services stopped"

# Restart all services
restart: down up

# Clean up
clean:
	@echo "Cleaning up $(ENV) environment..."
	$(DOCKER_COMPOSE) down -v --remove-orphans
	@echo "All containers, networks, and volumes removed"

# Show logs
logs:
	$(DOCKER_COMPOSE) logs -f

# Show logs for a specific service
logs-%:
	$(DOCKER_COMPOSE) logs -f $*

# Show running services
ps:
	$(DOCKER_COMPOSE) ps

# Initialize Airflow
init:
	@echo "Initializing Airflow in $(ENV) environment..."
	@if [ "$(ENV)" = "dev" ]; then \
		$(DOCKER_COMPOSE) down --remove-orphans airflow; \
	else \
		$(DOCKER_COMPOSE) down --remove-orphans airflow-webserver airflow-scheduler; \
	fi
	$(DOCKER_COMPOSE) up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@timeout=60; counter=0; \
	until $(DOCKER_COMPOSE) exec postgres pg_isready -U airflow 2>/dev/null || [ $$counter -eq $$timeout ]; do \
		counter=$$((counter+1)); \
		echo "PostgreSQL is unavailable - waiting ($$counter/$$timeout)..."; \
		sleep 1; \
	done; \
	if [ $$counter -eq $$timeout ]; then \
		echo "Error: PostgreSQL failed to start after $$timeout seconds"; \
		exit 1; \
	fi
	@echo "PostgreSQL is ready!"
	
	@if [ "$(ENV)" = "dev" ]; then \
		$(DOCKER_COMPOSE) run --rm airflow airflow db migrate && \
		$(DOCKER_COMPOSE) run --rm airflow airflow users create \
			--username "$${AIRFLOW_USER:-admin}" \
			--firstname "$${AIRFLOW_FIRST_NAME:-Admin}" \
			--lastname "$${AIRFLOW_LAST_NAME:-User}" \
			--role Admin \
			--email "$${AIRFLOW_USER_EMAIL:-admin@example.com}" \
			--password "$${AIRFLOW_PASSWORD:-admin}"; \
		$(DOCKER_COMPOSE) up -d airflow; \
	else \
		$(DOCKER_COMPOSE) run --rm airflow-webserver airflow db migrate && \
		$(DOCKER_COMPOSE) run --rm airflow-webserver airflow users create \
			--username "$${AIRFLOW_USER:-admin}" \
			--firstname "$${AIRFLOW_FIRST_NAME:-Admin}" \
			--lastname "$${AIRFLOW_LAST_NAME:-User}" \
			--role Admin \
			--email "$${AIRFLOW_USER_EMAIL:-admin@example.com}" \
			--password "$${AIRFLOW_PASSWORD:-admin}"; \
		$(DOCKER_COMPOSE) up -d airflow-webserver airflow-scheduler; \
	fi
	@echo "Airflow initialized with admin user from .env"

# Display Airflow auto-generated credentials
airflow-creds:
	@echo "Retrieving Airflow credentials..."
	@echo "----------------------------------------"
	@AUTH_LINE=$$($(DOCKER_COMPOSE) logs airflow 2>&1 | grep "Simple auth manager" | tail -1); \
	if [ -z "$$AUTH_LINE" ]; then \
		echo "❌ No auto-generated credentials found in logs."; \
		echo "This may mean you're using fixed credentials from .env"; \
		echo "or the container hasn't logged the credentials yet."; \
	else \
		echo "✅ Airflow Credentials:"; \
		echo "Username: $$(echo $$AUTH_LINE | grep -o "user '[^']*'" | cut -d "'" -f 2)"; \
		echo "Password: $$(echo $$AUTH_LINE | grep -o "Password for user '[^']*': [^ ]*" | awk -F': ' '{print $$2}')"; \
	fi
	@echo "----------------------------------------"
	@echo "These are either the auto-generated credentials OR"
	@echo "if you set _AIRFLOW_WWW_USER_* variables, check your .env file."

# Shell access to containers
airflow-shell:
	$(DOCKER_COMPOSE) exec $(AIRFLOW_SERVICE) bash

mlflow-shell:
	$(DOCKER_COMPOSE) exec mlflow sh

streamlit-shell:
	$(DOCKER_COMPOSE) exec streamlit bash

backend-shell:
	$(DOCKER_COMPOSE) exec backend bash

# Build commands
build:
	@echo "Building all services for $(ENV) environment..."
	$(DOCKER_COMPOSE) build
	@echo "Build complete"

build-fast:
	@echo "Building services with optimized settings..."
	DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 $(DOCKER_COMPOSE) build
	@echo "Build complete"

build-prod:
	@echo "Building production-optimized images..."
	DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 $(DOCKER_COMPOSE) build --pull
	@echo "Production build complete"

rebuild:
	@echo "Rebuilding all services for $(ENV) environment without cache..."
	$(DOCKER_COMPOSE) build --no-cache
	@echo "Rebuild complete"

# Resource management
purge:
	@echo "Purging all Docker resources related to this project..."
	docker compose -f docker-compose.base.yml -f docker-compose.dev.yml down -v --rmi all --remove-orphans
	docker compose -f docker-compose.base.yml -f docker-compose.prod.yml down -v --rmi all --remove-orphans
	@echo "Purge complete"

prune:
	@echo "Pruning unused Docker resources..."
	docker system prune -f
	@echo "Prune complete"


# Code Quality and Testing
.PHONY: test test-unit test-integration test-all lint format type-check security-check quality-check install-dev install-hooks

# Development setup
install-dev:
	@echo "Installing development dependencies..."
	pip install -r requirements-test.txt
	pip install pre-commit
	@echo "Development dependencies installed"

install-hooks:
	@echo "Installing pre-commit hooks..."
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "Pre-commit hooks installed"

# Testing
test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v --cov=src --cov=api --cov-report=html --cov-report=term-missing

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -v

test-all: test-unit test-integration
	@echo "All tests completed"

test: test-unit
	@echo "Quick test suite completed"

# Code quality
format:
	@echo "Formatting code with black..."
	black .
	@echo "Sorting imports with isort..."
	isort .
	@echo "Code formatting completed"

lint:
	@echo "Running flake8..."
	flake8 .
	@echo "Linting completed"

type-check:
	@echo "Running mypy type checks..."
	mypy api/ plugins/src/ --ignore-missing-imports
	@echo "Type checking completed"

security-check:
	@echo "Running security checks with bandit..."
	bandit -r . -f json -o bandit-report.json || true
	bandit -r . || true
	@echo "Running safety check..."
	safety check || true
	@echo "Security checks completed"

quality-check: format lint type-check security-check
	@echo "Full quality check completed"

# Pre-commit
pre-commit-run:
	@echo "Running pre-commit on all files..."
	pre-commit run --all-files

pre-commit-update:
	@echo "Updating pre-commit hooks..."
	pre-commit autoupdate

# Coverage
coverage-report:
	@echo "Generating coverage report..."
	pytest tests/unit/ --cov=src --cov=api --cov-report=html
	@echo "Coverage report generated in htmlcov/"

# Clean test artifacts
clean-test:
	@echo "Cleaning test artifacts..."
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -f bandit-report.json
	rm -f safety-report.json
	@echo "Test artifacts cleaned"

# Development workflow
dev-setup: install-dev install-hooks
	@echo "Development environment setup completed"

dev-check: quality-check test-all
	@echo "Development checks completed - ready to commit!"

# Help for code quality commands
help-quality:
	@echo "Code Quality Commands:"
	@echo "  install-dev       Install development dependencies"
	@echo "  install-hooks     Install pre-commit hooks"
	@echo "  dev-setup         Complete development setup"
	@echo "  test              Run quick unit tests"
	@echo "  test-unit         Run unit tests with coverage"
	@echo "  test-integration  Run integration tests"
	@echo "  test-all          Run all tests"
	@echo "  format            Format code with black and isort"
	@echo "  lint              Run flake8 linting"
	@echo "  type-check        Run mypy type checking"
	@echo "  security-check    Run bandit and safety security checks"
	@echo "  quality-check     Run all code quality checks"
	@echo "  pre-commit-run    Run pre-commit on all files"
	@echo "  coverage-report   Generate HTML coverage report"
	@echo "  dev-check         Run all quality checks and tests"
	@echo "  clean-test        Clean test artifacts"