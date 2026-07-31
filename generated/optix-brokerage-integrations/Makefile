# OPTIX Brokerage Integrations - Makefile
# Convenient commands for development and testing

.PHONY: help install test test-unit test-integration test-security coverage clean lint format run docker-build docker-up docker-down docs

# Default target
help:
	@echo "OPTIX Brokerage Integrations - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install          Install dependencies"
	@echo "  make run             Run the API server"
	@echo "  make format          Format code with black"
	@echo "  make lint            Lint code with flake8"
	@echo ""
	@echo "Testing:"
	@echo "  make test            Run all tests"
	@echo "  make test-unit       Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-security   Run security tests only"
	@echo "  make coverage        Run tests with coverage report"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    Build Docker image"
	@echo "  make docker-up       Start Docker containers"
	@echo "  make docker-down     Stop Docker containers"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean           Clean up generated files"
	@echo "  make docs            Generate documentation"

# Install dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# Run the API server
run:
	python -m uvicorn src.brokerage_service.api:app --reload --host 0.0.0.0 --port 8000

# Format code
format:
	black src/ tests/
	isort src/ tests/

# Lint code
lint:
	flake8 src/ tests/ --max-line-length=100
	mypy src/ --ignore-missing-imports

# Run all tests
test:
	pytest

# Run unit tests only
test-unit:
	pytest tests/unit/ -v

# Run integration tests only
test-integration:
	pytest tests/integration/ -v

# Run security tests only
test-security:
	pytest tests/unit/test_security.py -v

# Run tests with coverage
coverage:
	pytest --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build

# Docker commands
docker-build:
	docker build -t optix-brokerage:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Generate documentation
docs:
	@echo "Documentation files:"
	@echo "  - README.md"
	@echo "  - docs/TECHNICAL_REQUIREMENTS.md"
	@echo "  - docs/API_GUIDE.md"
	@echo "  - docs/DEPLOYMENT.md"
	@echo "  - IMPLEMENTATION_SUMMARY.md"

# Quick start for new developers
quickstart: install
	@echo "Creating .env file from example..."
	@cp -n .env.example .env || true
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your API credentials"
	@echo "  2. Start PostgreSQL and Redis"
	@echo "  3. Run: make run"
	@echo "  4. Visit: http://localhost:8000/docs"

# Database commands
db-migrate:
	alembic upgrade head

db-rollback:
	alembic downgrade -1

db-reset:
	alembic downgrade base
	alembic upgrade head

# Generate encryption key
generate-key:
	@python -c "from src.brokerage_service.encryption import TokenEncryption; print('TOKEN_ENCRYPTION_KEY=' + TokenEncryption.generate_key())"
