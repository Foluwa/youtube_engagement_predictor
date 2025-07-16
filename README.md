# YouTube Engagement Predictor

A production-ready MLOps system that predicts YouTube video engagement rates using machine learning. This end-to-end solution combines real-time prediction APIs, automated model training pipelines, and comprehensive monitoring to help content creators optimize their video performance.

## Problem Statement

YouTube content creators and marketing teams face a critical challenge: predicting how well their videos will perform before publishing. With over 500 hours of content uploaded every minute, understanding what drives engagement is crucial for:

- **Content Strategy**: Optimizing titles, tags, and posting schedules
- **Resource Allocation**: Focusing effort on high-potential content
- **Performance Benchmarking**: Setting realistic engagement expectations
- **A/B Testing**: Comparing different content approaches

This project solves these challenges by predicting the **like-to-view ratio** of YouTube videos based on metadata available at upload time, enabling data-driven content decisions.

## Dataset

Download and unzip into the `data` directory or run the `scripts/download_data.py` script.

**Source**: [YouTube Trending Video Dataset (Kaggle)](https://www.kaggle.com/datasets/datasnaek/youtube-new)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Pipeline                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Data Ingestion│  Feature Eng.   │    Model Training           │
│   (Kaggle API)  │  (Airflow)      │    (LightGBM + MLflow)      │
└─────────────────┴─────────────────┴─────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Serving Layer                                │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   FastAPI       │   Streamlit     │    Model Registry           │
│   (REST API)    │   (Web UI)      │    (MLflow)                 │
└─────────────────┴─────────────────┴─────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Monitoring & Alerting                          │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Data Drift    │   Performance   │    Automated Retraining     │
│   (Evidently)   │   (Telegram)    │    (Airflow)                │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## Key Features

- **Real-time Predictions**: REST API for instant engagement predictions
- **Batch Processing**: Automated daily model training and evaluation
- **Data Drift Monitoring**: Automatic detection of model degradation
- **Interactive Dashboard**: Web interface for exploratory predictions
- **Alert System**: Telegram notifications for model performance issues
- **Experiment Tracking**: Complete MLflow integration for reproducibility
- **Container Orchestration**: Production-ready Docker deployment
- **Comprehensive Testing**: Unit and integration test suites
- **CI/CD Pipeline**: Automated testing and deployment workflows
- **Code Quality**: Linting, formatting, and security checks

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **ML Framework** | LightGBM, scikit-learn | Model training and prediction |
| **Experiment Tracking** | MLflow | Model versioning and metrics |
| **Orchestration** | Apache Airflow | Workflow automation |
| **API Framework** | FastAPI | REST API serving |
| **Frontend** | Streamlit | Interactive web interface |
| **Monitoring** | Evidently | Data drift detection |
| **Database** | PostgreSQL | Airflow metadata storage |
| **Cache** | Redis | Performance optimization |
| **Containerization** | Docker, Docker Compose | Deployment and scaling |
| **Alerting** | Telegram Bot API | Real-time notifications |
| **Testing** | pytest, pytest-cov | Unit and integration testing |
| **Code Quality** | black, flake8, isort, mypy | Code formatting and linting |
| **CI/CD** | GitHub Actions | Automated testing and deployment |

## Prerequisites

- **Docker** (≥20.10) and **Docker Compose** (≥2.0)
- **Make** (for command automation)
- **Git** (for cloning the repository)
- **8GB RAM** minimum (for local development)
- **YouTube Data API Key** (optional, for real video fetching)
- **Kaggle API Credentials** (for data download)

## Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/Foluwa/youtube_engagement_predictor.git
cd youtube_engagement_predictor

# Complete development environment setup
make dev-setup
```

### 2. Configure Environment
Edit the generated `.env` file with your credentials:
```bash
# Required: Airflow Configuration
AIRFLOW_USER=admin
AIRFLOW_PASSWORD=secure_password_here
AIRFLOW_FIRST_NAME=Admin
AIRFLOW_LAST_NAME=User
AIRFLOW_USER_EMAIL=admin@yourcompany.com

# Optional: API Keys
YOUTUBE_API_KEY=your_youtube_api_key_here
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_api_key

# Optional: Monitoring Alerts
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
RMSE_ALERT_THRESHOLD=0.04
```

### 3. Start Development Environment
```bash
# Start all services
make dev

# Access points:
# - API: http://localhost:8000
# - Web UI: http://localhost:8501
# - Airflow: http://localhost:8080
# - MLflow: http://localhost:5001
```

## Detailed Setup Instructions

### Development Environment

1. **Initialize Airflow Database**
   ```bash
   make init
   ```

2. **Download Training Data**
   ```bash
   # Access Airflow container
   make shell-airflow

   # Inside container, run data download
   python scripts/download_data.py
   exit
   ```

3. **Run Initial Model Training**
   ```bash
   # Trigger training pipeline in Airflow UI
   # Or manually via shell:
   make shell-airflow
   python -c "from src.preprocess import preprocess; from src.train import train_model; preprocess(); train_model('data/processed.csv', 'models/model.pkl')"
   ```

### Production Environment

1. **Deploy to Production**
   ```bash
   make prod
   ```

2. **Verify Health Checks**
   ```bash
   # Check all services are running
   make ps

   # View logs
   make logs
   ```

3. **Monitor Performance**
   ```bash
   # Check drift reports
   make shell-airflow
   ls monitoring/
   ```

## Usage Examples

### API Usage

**Health Check**
```bash
curl http://localhost:8000/health
```

**Manual Prediction**
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Amazing Python Tutorial for Beginners",
    "tags": ["python", "tutorial", "programming"],
    "publish_time": "2025-07-14T10:00:00",
    "category_name": "Education"
  }'
```

**YouTube URL Prediction**
```bash
curl -X POST "http://localhost:8000/fetch-and-predict" \
  -H "Content-Type: application/json" \
  -d '{"video_id": "dQw4w9WgXcQ"}'
```

### Web Interface

1. Navigate to http://localhost:8501
2. Choose input mode:
   - **Manual Entry**: Input video metadata directly
   - **YouTube URL**: Fetch real video data and predict
3. View predictions and historical performance

### Model Training

**Manual Training**
```python
from src.preprocess import preprocess
from src.train import train_model

# Process raw data
preprocess('data/raw', 'data/processed.csv')

# Train new model
train_model('data/processed.csv', 'models/model.pkl')
```

**Automated Training** (via Airflow)
- Daily: Data processing and validation
- Weekly: Model retraining
- On-demand: Triggered by monitoring alerts

## Make Commands Reference

### Environment Management
```bash
make setup           # Create .env file from template
make dev-setup       # Complete development environment setup
make dev             # Start development environment
make prod            # Start production environment
make up ENV=dev      # Start specific environment
make down            # Stop all services
make restart         # Restart all services
make clean           # Stop and remove containers/volumes
```

### Service Operations
```bash
make ps              # Show running services
make logs            # Show logs from all services
make logs-airflow    # Show logs from specific service
make logs-backend    # Show backend API logs
make logs-streamlit  # Show Streamlit logs
```

### Container Access
```bash
make shell-airflow   # Access Airflow container
make shell-backend   # Access FastAPI container
make shell-streamlit # Access Streamlit container
make shell-mlflow    # Access MLflow container
```

### Build Operations
```bash
make build           # Build all services
make build-fast      # Build with optimizations
make build-prod      # Build production images
make rebuild         # Rebuild without cache
```

### Testing & Quality Assurance
```bash
make test            # Run quick test suite
make test-unit       # Run unit tests with coverage
make test-integration # Run integration tests
make test-cov        # Run tests with HTML coverage report
make coverage-report # Generate HTML coverage report
```

### Code Quality
```bash
make format          # Format code with black and isort
make lint            # Run linting with flake8
make type-check      # Run type checking with mypy
make security-check  # Run security checks with bandit and safety
make quality         # Run all quality checks
```

### Development Workflows
```bash
make dev-check       # Run all checks before committing
make ci-check        # Lightweight CI checks
make pre-commit-run  # Run pre-commit on all files
```

### Airflow Management
```bash
make init            # Initialize Airflow database and admin user
make airflow-creds   # Display Airflow login credentials
```

### Resource Management
```bash
make clean-test      # Clean test artifacts
make prune           # Clean unused Docker resources
make purge           # Remove all project containers and images
```

## Testing Framework

### Running Tests

The project includes comprehensive test coverage:

```bash
# Quick test suite
make test

# Run specific test types
make test-unit        # Unit tests with coverage
make test-integration # Integration tests
make test-cov         # Generate coverage report
```

### Test Structure

- **Unit Tests**: Test individual components and functions
- **Integration Tests**: Test end-to-end workflows and API endpoints
- **Coverage Reports**: HTML reports generated in `htmlcov/`

### Continuous Integration

GitHub Actions pipeline automatically:
- Runs linting and formatting checks
- Executes full test suite
- Builds and validates Docker images
- Generates coverage reports

## Monitoring and Alerting

### Data Drift Detection
- **Frequency**: Daily automated checks
- **Method**: Evidently reports comparing recent data to reference dataset
- **Output**: HTML reports in `monitoring/drift_report.html`

### Performance Monitoring
- **Metric**: RMSE (Root Mean Square Error)
- **Threshold**: Configurable via `RMSE_ALERT_THRESHOLD` (default: 0.04)
- **Alerts**: Telegram notifications when threshold exceeded

### Model Retraining
- **Trigger**: Weekly schedule or manual intervention
- **Process**: Automated via Airflow DAG
- **Validation**: Automatic model comparison and deployment

## API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/predict` | POST | Predict engagement from metadata |
| `/fetch-and-predict` | POST | Fetch YouTube video and predict |

## Code Quality Standards

The project enforces high code quality through:

- **Formatting**: Black for code formatting, isort for import sorting
- **Linting**: Flake8 for style guide enforcement
- **Type Checking**: MyPy for static type analysis
- **Security**: Bandit for security vulnerability scanning
- **Testing**: pytest with coverage requirements
- **Pre-commit Hooks**: Automated quality checks before commits

## Troubleshooting

### Common Issues

**Port Conflicts**
```bash
# Check what's using the ports
lsof -i :8080,8000,8501,5001

# Or change ports in docker-compose files
```

**Memory Issues**
```bash
# Check Docker memory usage
docker stats

# Increase Docker memory limit in Docker Desktop settings
```

**Database Connection Issues**
```bash
# Reset Airflow database
make clean
make init
```

**Model Loading Errors**
```bash
# Check if model file exists
make shell-backend
ls -la models/

# Retrain model if missing
make shell-airflow
python -c "from src.train import train_model; train_model('data/processed.csv', 'models/model.pkl')"
```

### Getting Help

1. **Check logs**: `make logs-[service]`
2. **Verify environment**: Ensure `.env` file is properly configured
3. **Resource check**: Ensure sufficient memory and disk space
4. **Clean restart**: `make clean && make dev`

## Project Structure

```
├── .github/                     # GitHub Actions CI/CD
│   └── workflows/
│       └── ci.yml              # Automated testing pipeline
├── api/                        # FastAPI application
│   └── main.py                 # REST API endpoints
├── dags/                       # Airflow DAGs
│   ├── monitor_dag.py          # Data drift monitoring
│   ├── retrain_dag.py          # Automated retraining
│   └── train_dag.py            # Model training pipeline
├── logs/                       # Airflow logs
│   ├── dag_processor/
│   └── scheduler/
├── plugins/                    # Airflow plugins
│   └── src/                    # Core ML modules
│       ├── __init__.py
│       ├── ingest.py           # Data ingestion
│       ├── monitor.py          # Monitoring logic
│       ├── predict.py          # Prediction utilities
│       ├── preprocess.py       # Data preprocessing
│       └── train.py            # Model training
├── scripts/                    # Utility scripts
│   └── download_data.py        # Kaggle data downloader
├── tests/                      # Test suite
│   ├── integration/            # Integration tests
│   │   ├── __init__.py
│   │   └── test_api.py
│   ├── unit/                   # Unit tests
│   │   ├── __init__.py
│   │   └── test_core.py
│   ├── __init__.py
│   └── conftest.py             # Test configuration
├── .bandit                     # Security scan configuration
├── .dockerignore               # Docker ignore patterns
├── .env.example                # Environment template
├── .flake8                     # Linting configuration
├── .gitignore                  # Git ignore patterns
├── .pre-commit-config.yaml     # Pre-commit hooks
├── docker-compose.base.yml     # Base Docker services
├── docker-compose.dev.yml      # Development overrides
├── docker-compose.prod.yml     # Production overrides
├── Dockerfile                  # Main application container
├── Dockerfile.airflow          # Airflow container
├── Dockerfile.streamlit        # Streamlit container
├── Makefile                    # Command automation
├── pyproject.toml              # Python project configuration
├── README.md                   # Project documentation
├── requirements-airflow.txt    # Airflow dependencies
├── requirements-test.txt       # Testing dependencies
├── requirements.txt            # Main dependencies
├── streamlit_app.py            # Web interface
└── streamlit-requirements.txt  # Streamlit dependencies
```

## Contributing

### Development Workflow

1. **Setup Development Environment**
   ```bash
   make dev-setup
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Changes and Test**
   ```bash
   make dev-check  # Run all quality checks
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Standards

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write comprehensive tests for new features
- Update documentation for API changes
- Ensure all quality checks pass before submitting

## Acknowledgments

- **YouTube Data API** for video metadata access
- **Evidently** for drift detection capabilities
- **MLflow** for experiment tracking
- **Apache Airflow** for workflow orchestration
- **MLOps Zoomcamp** for project inspiration and guidance

---

**Built with ❤️ for the MLOps community**

*For questions or support, please open an issue or contact [moronfoluwaakintola@gmail.com](mailto:moronfoluwaakintola@gmail.com)*
