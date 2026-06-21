.PHONY: dev dev.up dev.run test lint clean help

help:
	@echo "FODEJAS Development Commands"
	@echo ""
	@echo "  make dev       - Start full development environment (Docker + Django)"
	@echo "  make dev.up    - Start Docker services only"
	@echo "  make dev.run   - Start Django development server only"
	@echo "  make test      - Run pytest"
	@echo "  make lint      - Run ruff, black, and isort"
	@echo "  make clean     - Remove temporary files"
	@echo ""

dev:
	./scripts/dev.sh

dev.up:
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml up -d

dev.run:
	python manage.py runserver 0.0.0.0:8000

test:
	pytest

lint:
	ruff check .
	black --check .
	isort --check .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.coverage" -delete 2>/dev/null || true
