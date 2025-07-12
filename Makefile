# YouTube Engagement Predictor
.PHONY: up down restart clean logs ps init airflow-shell mlflow-shell streamlit-shell backend-shell build rebuild help

# Default target
.DEFAULT_GOAL := help

# Docker Compose command with env file
DOCKER_COMPOSE = docker compose

# Services
SERVICES = backend streamlit mlflow postgres redis airflow-webserver airflow-scheduler

# Help command
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  up              Start all services"
	@echo "  down            Stop all services"
	@echo "  restart         Restart all services"
	@echo "  clean           Stop and remove all containers, networks, and volumes"
	@echo "  logs            Show logs from all services"
	@echo "  logs-service    Show logs from a specific service (e.g., make logs-airflow-webserver)"
	@echo "  ps              Show running services"
	@echo "  init            Initialize Airflow database and create admin user"
	@echo "  airflow-shell   Open a shell in the Airflow webserver container"
	@echo "  mlflow-shell    Open a shell in the MLflow container"
	@echo "  streamlit-shell Open a shell in the Streamlit container"
	@echo "  backend-shell   Open a shell in the backend container"
	@echo "  build           Build all services"
	@echo "  rebuild         Rebuild all services (no cache)"
	@echo "  purge           Remove all containers, networks, volumes, and images"

# Start all services
up:
	@echo "Starting all services..."
	$(DOCKER_COMPOSE) up -d postgres redis
	@sleep 5  # Wait for the database to be ready
	$(DOCKER_COMPOSE) up -d mlflow backend streamlit
	@sleep 3  # Wait for backend services to be ready
	$(DOCKER_COMPOSE) up -d airflow-webserver airflow-scheduler
	@echo "Services started. Access points:"
	@echo "  - Backend: http://localhost:80"
	@echo "  - Streamlit: http://localhost:8501"
	@echo "  - MLflow: http://localhost:5001"
	@echo "  - Airflow: http://localhost:8080"

# Stop all services
down:
	@echo "Stopping all services..."
	$(DOCKER_COMPOSE) down
	@echo "All services stopped"

# Restart all services
restart: down up

# Clean up
clean:
	@echo "Cleaning up..."
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
	@echo "Initializing Airflow..."
	$(DOCKER_COMPOSE) down -v --remove-orphans airflow-webserver airflow-scheduler
	$(DOCKER_COMPOSE) up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@timeout=60; counter=0; \
	until docker compose exec postgres pg_isready -U airflow || [ $$counter -eq $$timeout ]; do \
		counter=$$((counter+1)); \
		echo "PostgreSQL is unavailable - waiting ($$counter/$$timeout)..."; \
		sleep 1; \
	done; \
	if [ $$counter -eq $$timeout ]; then \
		echo "Error: PostgreSQL failed to start after $$timeout seconds"; \
		exit 1; \
	fi
	@echo "PostgreSQL is ready!"
	$(DOCKER_COMPOSE) run --rm airflow-init
	$(DOCKER_COMPOSE) up -d airflow-webserver airflow-scheduler
	@echo "Airflow initialized with admin user from .env"

# Open a shell in Airflow webserver
airflow-shell:
	$(DOCKER_COMPOSE) exec airflow-webserver bash

# Open a shell in MLflow
mlflow-shell:
	$(DOCKER_COMPOSE) exec mlflow sh

# Open a shell in Streamlit
streamlit-shell:
	$(DOCKER_COMPOSE) exec streamlit bash

# Open a shell in backend
backend-shell:
	$(DOCKER_COMPOSE) exec backend bash

# Build all services
build:
	@echo "Building all services..."
	$(DOCKER_COMPOSE) build
	@echo "Build complete"

# Rebuild all services (no cache)
rebuild:
	@echo "Rebuilding all services without cache..."
	$(DOCKER_COMPOSE) build --no-cache
	@echo "Rebuild complete"

# Complete purge (containers, networks, volumes, and images)
purge:
	@echo "Purging all Docker resources related to this project..."
	$(DOCKER_COMPOSE) down -v --rmi all --remove-orphans
	@echo "Purge complete"

# Additional useful commands

# Airflow check
airflow-check:
	$(DOCKER_COMPOSE) exec airflow-webserver airflow info

# Database backup
db-backup:
	@echo "Creating database backup..."
	$(DOCKER_COMPOSE) exec postgres pg_dump -U airflow airflow > backup_$(shell date +%Y%m%d%H%M%S).sql
	@echo "Backup created"

# Database restore (usage: make db-restore BACKUP=backup_file.sql)
db-restore:
	@echo "Restoring database from $(BACKUP)..."
	cat $(BACKUP) | $(DOCKER_COMPOSE) exec -T postgres psql -U airflow airflow
	@echo "Restore complete"