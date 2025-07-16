# YouTube Engagement Predictor
# Professional Makefile with organized commands and no duplication

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default target
.DEFAULT_GOAL := help

# Environment variables
ENV ?= dev
PYTHON ?= python3
PIP ?= pip

# Docker configuration
DOCKER_COMPOSE = docker compose -f docker-compose.base.yml -f docker-compose.$(ENV).yml --env-file .env

# Service configuration based on environment
ifeq ($(ENV),dev)
	AIRFLOW_SERVICE = airflow
	BACKEND_PORT = 8000
else
	AIRFLOW_SERVICE = airflow-webserver
	BACKEND_PORT = 80
endif

# Colors for output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
MAGENTA := \033[35m
CYAN := \033[36m
WHITE := \033[37m
RESET := \033[0m

# =============================================================================
# PHONY TARGETS
# =============================================================================

.PHONY: help setup \
        dev prod up down restart clean purge prune \
        init logs logs-% ps \
        build build-fast build-prod rebuild \
        shell-% \
        install-dev install-hooks dev-setup \
        test test-unit test-integration test-cov \
        lint format type-check security-check quality \
        pre-commit-run pre-commit-update \
        coverage-report clean-test \
        airflow-creds

# =============================================================================
# HELP & DOCUMENTATION
# =============================================================================

help: ## Show this help message
	@echo "$(CYAN)YouTube Engagement Predictor$(RESET)"
	@echo "$(YELLOW)Usage: make [target] [ENV=dev|prod]$(RESET)"
	@echo ""
	@echo "$(MAGENTA)🚀 Quick Start:$(RESET)"
	@echo "  $(GREEN)make dev-setup$(RESET)     Complete development environment setup"
	@echo "  $(GREEN)make dev$(RESET)           Start development environment"
	@echo "  $(GREEN)make test$(RESET)          Run tests"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { \
		group = ""; \
		if (match($$1, /^([a-z-]+)-/)) { \
			group = substr($$1, RSTART, RLENGTH-1); \
		} \
		if (group != last_group) { \
			if (last_group != "") print ""; \
			printf "$(BLUE)%s:$(RESET)\n", toupper(group); \
			last_group = group; \
		} \
		printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2 \
	}' $(MAKEFILE_LIST)

# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

setup: ## Create .env file from template
	@echo "$(YELLOW)Setting up environment configuration...$(RESET)"
	@if [ ! -f .env ] && [ -f .env.example ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env file created from .env.example$(RESET)"; \
		echo "$(YELLOW)⚠ Please update .env with your actual values$(RESET)"; \
	elif [ ! -f .env ]; then \
		echo "$(YELLOW)Creating default .env file...$(RESET)"; \
		echo "POSTGRES_USER=airflow\nPOSTGRES_PASSWORD=airflow\nPOSTGRES_DB=airflow\n\nAIRFLOW_USER=admin\nAIRFLOW_FIRST_NAME=Admin\nAIRFLOW_LAST_NAME=User\nAIRFLOW_USER_EMAIL=admin@example.com\nAIRFLOW_PASSWORD=admin" > .env; \
		echo "$(GREEN)✓ Default .env file created$(RESET)"; \
	else \
		echo "$(GREEN)✓ .env file already exists$(RESET)"; \
	fi

install-dev: ## Install development dependencies
	@echo "$(YELLOW)Installing development dependencies...$(RESET)"
	@$(PIP) install -r requirements-test.txt
	@$(PIP) install pre-commit mypy bandit safety
	@echo "$(GREEN)✓ Development dependencies installed$(RESET)"

install-hooks: install-dev ## Install pre-commit hooks
	@echo "$(YELLOW)Installing pre-commit hooks...$(RESET)"
	@pre-commit install
	@pre-commit install --hook-type commit-msg
	@echo "$(GREEN)✓ Pre-commit hooks installed$(RESET)"

dev-setup: setup install-hooks ## Complete development environment setup
	@echo "$(GREEN)✅ Development environment setup completed$(RESET)"

# =============================================================================
# DOCKER OPERATIONS
# =============================================================================

dev: ## Start development environment
	@$(MAKE) up ENV=dev

prod: ## Start production environment
	@$(MAKE) up ENV=prod

up: setup ## Start all services
	@echo "$(YELLOW)Starting all services in $(ENV) environment...$(RESET)"
	@$(DOCKER_COMPOSE) up -d postgres redis
	@$(MAKE) _wait-for-postgres
	@$(DOCKER_COMPOSE) up -d mlflow backend streamlit
	@sleep 3
	@$(DOCKER_COMPOSE) up -d $(AIRFLOW_SERVICE)
	@echo "$(GREEN)✅ Environment started successfully$(RESET)"
	@$(MAKE) _show-endpoints

down: ## Stop all services
	@echo "$(YELLOW)Stopping all services in $(ENV) environment...$(RESET)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ All services stopped$(RESET)"

restart: down up ## Restart all services

clean: ## Stop and remove containers, networks, and volumes
	@echo "$(YELLOW)Cleaning up $(ENV) environment...$(RESET)"
	@$(DOCKER_COMPOSE) down -v --remove-orphans
	@echo "$(GREEN)✓ All containers, networks, and volumes removed$(RESET)"

# =============================================================================
# BUILD OPERATIONS
# =============================================================================

build: ## Build all services
	@echo "$(YELLOW)Building all services for $(ENV) environment...$(RESET)"
	@$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✓ Build complete$(RESET)"

build-fast: ## Build with BuildKit optimizations
	@echo "$(YELLOW)Building services with optimizations...$(RESET)"
	@DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 $(DOCKER_COMPOSE) build
	@echo "$(GREEN)✓ Optimized build complete$(RESET)"

build-prod: ## Build production-ready images
	@echo "$(YELLOW)Building production-optimized images...$(RESET)"
	@DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 $(DOCKER_COMPOSE) build --pull
	@echo "$(GREEN)✓ Production build complete$(RESET)"

rebuild: ## Rebuild all services without cache
	@echo "$(YELLOW)Rebuilding all services without cache...$(RESET)"
	@$(DOCKER_COMPOSE) build --no-cache
	@echo "$(GREEN)✓ Rebuild complete$(RESET)"

# =============================================================================
# AIRFLOW OPERATIONS
# =============================================================================

init: ## Initialize Airflow database and create admin user
	@echo "$(YELLOW)Initializing Airflow in $(ENV) environment...$(RESET)"
	@$(MAKE) _stop-airflow
	@$(DOCKER_COMPOSE) up -d postgres
	@$(MAKE) _wait-for-postgres
	@$(MAKE) _init-airflow-db
	@$(MAKE) _start-airflow
	@echo "$(GREEN)✅ Airflow initialized successfully$(RESET)"

airflow-creds: ## Display Airflow login credentials
	@echo "$(CYAN)Airflow Credentials:$(RESET)"
	@echo "$(YELLOW)----------------------------------------$(RESET)"
	@AUTH_LINE=$$($(DOCKER_COMPOSE) logs $(AIRFLOW_SERVICE) 2>&1 | grep "Simple auth manager" | tail -1); \
	if [ -z "$$AUTH_LINE" ]; then \
		echo "$(RED)❌ No auto-generated credentials found$(RESET)"; \
		echo "$(YELLOW)Check your .env file for configured credentials$(RESET)"; \
	else \
		echo "$(GREEN)Username:$(RESET) $$(echo $$AUTH_LINE | grep -o "user '[^']*'" | cut -d "'" -f 2)"; \
		echo "$(GREEN)Password:$(RESET) $$(echo $$AUTH_LINE | grep -o "Password for user '[^']*': [^ ]*" | awk -F': ' '{print $$2}')"; \
	fi
	@echo "$(YELLOW)----------------------------------------$(RESET)"

# =============================================================================
# MONITORING & DEBUGGING
# =============================================================================

logs: ## Show logs from all services
	@$(DOCKER_COMPOSE) logs -f

logs-%: ## Show logs from specific service (e.g., make logs-airflow)
	@$(DOCKER_COMPOSE) logs -f $*

ps: ## Show running services
	@$(DOCKER_COMPOSE) ps

shell-%: ## Open shell in specific service (e.g., make shell-airflow)
	@case $* in \
		airflow) $(DOCKER_COMPOSE) exec $(AIRFLOW_SERVICE) bash ;; \
		backend) $(DOCKER_COMPOSE) exec backend bash ;; \
		streamlit) $(DOCKER_COMPOSE) exec streamlit bash ;; \
		mlflow) $(DOCKER_COMPOSE) exec mlflow sh ;; \
		*) echo "$(RED)❌ Unknown service: $*$(RESET)"; echo "$(YELLOW)Available: airflow, backend, streamlit, mlflow$(RESET)" ;; \
	esac

# =============================================================================
# TESTING
# =============================================================================

test: install-dev ## Run quick test suite
	@echo "$(YELLOW)Running test suite...$(RESET)"
	@pytest tests/ -v --tb=short
	@echo "$(GREEN)✅ Tests completed$(RESET)"

test-unit: install-dev ## Run unit tests with coverage
	@echo "$(YELLOW)Running unit tests...$(RESET)"
	@pytest tests/ -v -m "not integration" --cov=src --cov=api --cov-report=term-missing
	@echo "$(GREEN)✅ Unit tests completed$(RESET)"

test-integration: install-dev ## Run integration tests
	@echo "$(YELLOW)Running integration tests...$(RESET)"
	@pytest tests/ -v -m integration
	@echo "$(GREEN)✅ Integration tests completed$(RESET)"

test-cov: install-dev ## Run tests with HTML coverage report
	@echo "$(YELLOW)Running tests with coverage report...$(RESET)"
	@pytest tests/ -v --cov=src --cov=api --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✅ Coverage report generated in htmlcov/$(RESET)"

coverage-report: test-cov ## Generate HTML coverage report
	@echo "$(CYAN)📊 Coverage report available at htmlcov/index.html$(RESET)"

# =============================================================================
# CODE QUALITY
# =============================================================================

format: install-dev ## Format code with black and isort
	@echo "$(YELLOW)Formatting code...$(RESET)"
	@black . --exclude="venv|__pycache__|.git|.pytest_cache"
	@isort . --skip=venv --skip=__pycache__ --skip=.git --skip=.pytest_cache
	@echo "$(GREEN)✓ Code formatting completed$(RESET)"

lint: install-dev ## Run linting with flake8
	@echo "$(YELLOW)Running linting...$(RESET)"
	@flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	@flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics --exclude=venv,__pycache__,.git,.pytest_cache
	@echo "$(GREEN)✓ Linting completed$(RESET)"

type-check: install-dev ## Run type checking with mypy
	@echo "$(YELLOW)Running type checks...$(RESET)"
	@mypy api/ plugins/src/ --ignore-missing-imports || true
	@echo "$(GREEN)✓ Type checking completed$(RESET)"

security-check: install-dev ## Run security checks
	@echo "$(YELLOW)Running security checks...$(RESET)"
	@bandit -r . -f json -o bandit-report.json --exclude ./venv,./tests || true
	@bandit -r . --exclude ./venv,./tests || true
	@safety check || true
	@echo "$(GREEN)✓ Security checks completed$(RESET)"

quality: format lint type-check security-check test ## Run all quality checks
	@echo "$(GREEN)✅ All quality checks completed$(RESET)"

# =============================================================================
# PRE-COMMIT OPERATIONS
# =============================================================================

pre-commit-run: install-hooks ## Run pre-commit on all files
	@echo "$(YELLOW)Running pre-commit on all files...$(RESET)"
	@pre-commit run --all-files
	@echo "$(GREEN)✓ Pre-commit checks completed$(RESET)"

pre-commit-update: install-hooks ## Update pre-commit hooks
	@echo "$(YELLOW)Updating pre-commit hooks...$(RESET)"
	@pre-commit autoupdate
	@echo "$(GREEN)✓ Pre-commit hooks updated$(RESET)"

# =============================================================================
# CLEANUP OPERATIONS
# =============================================================================

clean-test: ## Clean test artifacts
	@echo "$(YELLOW)Cleaning test artifacts...$(RESET)"
	@rm -rf .pytest_cache/ .coverage htmlcov/ .mypy_cache/ *.egg-info/
	@rm -f bandit-report.json safety-report.json
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Test artifacts cleaned$(RESET)"

purge: ## Remove all Docker resources
	@echo "$(RED)⚠ This will remove ALL project containers and images$(RESET)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		docker compose -f docker-compose.base.yml -f docker-compose.dev.yml down -v --rmi all --remove-orphans; \
		docker compose -f docker-compose.base.yml -f docker-compose.prod.yml down -v --rmi all --remove-orphans; \
		echo "$(GREEN)✓ Purge completed$(RESET)"; \
	else \
		echo ""; \
		echo "$(YELLOW)Purge cancelled$(RESET)"; \
	fi

prune: ## Clean up unused Docker resources
	@echo "$(YELLOW)Pruning unused Docker resources...$(RESET)"
	@docker system prune -f
	@echo "$(GREEN)✓ Docker cleanup completed$(RESET)"

# =============================================================================
# DEVELOPMENT WORKFLOWS
# =============================================================================

dev-check: quality test-integration ## Run all checks before committing
	@echo "$(GREEN)✅ All development checks passed - ready to commit!$(RESET)"

ci-check: lint test ## Lightweight CI checks
	@echo "$(GREEN)✅ CI checks completed$(RESET)"

# =============================================================================
# INTERNAL/HELPER TARGETS
# =============================================================================

_wait-for-postgres:
	@echo "$(YELLOW)Waiting for PostgreSQL to be ready...$(RESET)"
	@timeout=60; counter=0; \
	until $(DOCKER_COMPOSE) exec postgres pg_isready -U airflow 2>/dev/null || [ $$counter -eq $$timeout ]; do \
		counter=$$((counter+1)); \
		printf "\r$(YELLOW)PostgreSQL starting... ($$counter/$$timeout)$(RESET)"; \
		sleep 1; \
	done; \
	if [ $$counter -eq $$timeout ]; then \
		echo "\n$(RED)❌ PostgreSQL failed to start after $$timeout seconds$(RESET)"; \
		exit 1; \
	fi
	@echo "\n$(GREEN)✓ PostgreSQL is ready$(RESET)"

_stop-airflow:
	@if [ "$(ENV)" = "dev" ]; then \
		$(DOCKER_COMPOSE) stop airflow 2>/dev/null || true; \
	else \
		$(DOCKER_COMPOSE) stop airflow-webserver airflow-scheduler 2>/dev/null || true; \
	fi

_start-airflow:
	@if [ "$(ENV)" = "dev" ]; then \
		$(DOCKER_COMPOSE) up -d airflow; \
	else \
		$(DOCKER_COMPOSE) up -d airflow-webserver airflow-scheduler; \
	fi

_init-airflow-db:
	@if [ "$(ENV)" = "dev" ]; then \
		$(DOCKER_COMPOSE) run --rm airflow airflow db migrate && \
		$(DOCKER_COMPOSE) run --rm airflow airflow users create \
			--username "$${AIRFLOW_USER:-admin}" \
			--firstname "$${AIRFLOW_FIRST_NAME:-Admin}" \
			--lastname "$${AIRFLOW_LAST_NAME:-User}" \
			--role Admin \
			--email "$${AIRFLOW_USER_EMAIL:-admin@example.com}" \
			--password "$${AIRFLOW_PASSWORD:-admin}"; \
	else \
		$(DOCKER_COMPOSE) run --rm airflow-webserver airflow db migrate && \
		$(DOCKER_COMPOSE) run --rm airflow-webserver airflow users create \
			--username "$${AIRFLOW_USER:-admin}" \
			--firstname "$${AIRFLOW_FIRST_NAME:-Admin}" \
			--lastname "$${AIRFLOW_LAST_NAME:-User}" \
			--role Admin \
			--email "$${AIRFLOW_USER_EMAIL:-admin@example.com}" \
			--password "$${AIRFLOW_PASSWORD:-admin}"; \
	fi

_show-endpoints:
	@echo "$(CYAN)🌐 Service Endpoints:$(RESET)"
	@echo "  $(GREEN)Backend API:$(RESET)    http://localhost:$(BACKEND_PORT)"
	@echo "  $(GREEN)Streamlit UI:$(RESET)   http://localhost:8501"
	@echo "  $(GREEN)MLflow:$(RESET)         http://localhost:5001"
	@echo "  $(GREEN)Airflow:$(RESET)        http://localhost:8080"
