.PHONY: help up down build migrate seed seed-demo cluster test lint format clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Start all services with docker-compose
	docker compose up -d

down: ## Stop all services
	docker compose down

build: ## Build all docker images
	docker compose build

rebuild: ## Rebuild all docker images without cache
	docker compose build --no-cache

logs: ## Follow logs from all services
	docker compose logs -f

logs-api: ## Follow API logs
	docker compose logs -f api

logs-worker: ## Follow worker logs
	docker compose logs -f worker

ps: ## Show running services
	docker compose ps

migrate: ## Run database migrations
	docker compose exec api alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="your message")
	docker compose exec api alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback one migration
	docker compose exec api alembic downgrade -1

seed: ## Seed database with demo data (non-destructive)
	@echo "🌱 Seeding demo data..."
	@docker compose exec api python -m apps.api.scripts.seed_demo
	@echo ""
	@echo "✅ Validating seed results..."
	@docker compose exec -T api python -c "from apps.api.database import get_db_context; from apps.api.models import Feedback; \
	db_ctx = get_db_context(); db = db_ctx.__enter__(); \
	count = db.query(Feedback).count(); \
	print(f'📊 Total feedback items: {count}'); \
	db_ctx.__exit__(None, None, None); \
	exit(0 if count >= 40 else 1)" || (echo "❌ ERROR: Expected at least 40 feedback items. Seed may have failed." && exit 1)
	@echo "✅ Seed validation passed!"
	@echo ""
	@echo "🎯 Next step: Run 'make cluster' to generate insights"

seed-demo: seed ## Alias for seed

seed-clear: ## Clear all demo data and start fresh
	@echo "⚠️  WARNING: This will delete ALL data from the database!"
	@echo "Press Ctrl+C within 5 seconds to cancel..."
	@sleep 5
	@echo "🗑️  Clearing database..."
	@docker compose exec -T api python -c "from apps.api.database import get_db_context, engine; from apps.api.models import Base; \
	Base.metadata.drop_all(bind=engine); \
	Base.metadata.create_all(bind=engine); \
	print('✅ Database cleared successfully')"
	@echo "🔄 Running migrations..."
	@docker compose exec api alembic upgrade head
	@echo "✅ Database reset complete! Run 'make seed' to load demo data."

cluster: ## Run clustering pipeline on current data
	docker compose exec api python -m apps.api.scripts.run_clustering

ingest-slack: ## Ingest Slack data (demo or live based on DEMO_MODE)
	docker compose exec api python -m apps.api.scripts.ingest_slack

ingest-jira: ## Ingest Jira data (demo or live based on DEMO_MODE)
	docker compose exec api python -m apps.api.scripts.ingest_jira

test: ## Run all tests
	docker compose exec api pytest

test-cov: ## Run tests with coverage
	docker compose exec api pytest --cov=apps.api --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode
	docker compose exec api pytest-watch

lint: ## Run linting
	docker compose exec api ruff check apps/api
	docker compose exec api mypy apps/api

format: ## Format code
	docker compose exec api ruff format apps/api
	docker compose exec api ruff check --fix apps/api

shell-api: ## Open shell in API container
	docker compose exec api /bin/bash

shell-db: ## Open psql shell
	docker compose exec postgres psql -U produckai -d produckai

shell-redis: ## Open redis-cli
	docker compose exec redis redis-cli

clean: ## Clean up containers, volumes, and caches
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

install-dev: ## Install development dependencies locally (for IDE support)
	cd apps/api && pip install -e ".[dev]"

extension-build: ## Build Chrome extension
	cd apps/extension && npm install && npm run build

extension-dev: ## Build Chrome extension in dev mode
	cd apps/extension && npm install && npm run dev

web-build: ## Build Next.js app
	cd apps/web && npm install && npm run build

demo: up migrate seed cluster ## Quick start: bring up services, migrate, seed, and cluster
	@echo ""
	@echo "========================================="
	@echo "✅ ProduckAI Demo Mode Ready!"
	@echo "========================================="
	@echo ""
	@echo "📊 Backend API:  http://localhost:8000"
	@echo "🎨 Web UI:       http://localhost:3000"
	@echo "📚 API Docs:     http://localhost:8000/docs"
	@echo ""
	@echo "🎯 What's loaded:"
	@docker compose exec -T api python -c "from apps.api.database import get_db_context; from apps.api.models import Feedback, Customer; \
	from apps.api.models.theme import Theme, Insight; \
	db_ctx = get_db_context(); db = db_ctx.__enter__(); \
	feedback_count = db.query(Feedback).count(); \
	customer_count = db.query(Customer).count(); \
	theme_count = db.query(Theme).count(); \
	insight_count = db.query(Insight).count(); \
	print(f'   • {customer_count} demo customers'); \
	print(f'   • {feedback_count} feedback items'); \
	print(f'   • {theme_count} themes'); \
	print(f'   • {insight_count} insights'); \
	db_ctx.__exit__(None, None, None)"
	@echo ""
	@echo "🚀 Open http://localhost:3000 to explore!"
	@echo "========================================="

status: ## Check health of all services
	@echo "Checking service health..."
	@curl -s http://localhost:8000/healthz || echo "❌ API is down"
	@curl -s http://localhost:3000 > /dev/null && echo "✅ Web is up" || echo "❌ Web is down"
