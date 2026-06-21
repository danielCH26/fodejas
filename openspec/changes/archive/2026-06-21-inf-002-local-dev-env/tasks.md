## 1. Script: create_venv.sh

- [x] 1.1 Create scripts/create_venv.sh that creates .venv using python3 -m venv
- [x] 1.2 Install project with dev dependencies: pip install -e ".[dev]"
- [x] 1.3 Make script executable
- [x] 1.4 Verify script works on clean checkout

## 2. Script: wait_for_services.sh

- [x] 2.1 Create scripts/wait_for_services.sh with netcat-based port checking
- [x] 2.2 Support configurable host:port pairs via arguments
- [x] 2.3 Support configurable timeout (default 30s)
- [x] 2.4 Exit with error if any service fails to respond within timeout

## 3. Script: dev.sh

- [x] 3.1 Create scripts/dev.sh that starts Docker services with docker compose
- [x] 3.2 Call wait_for_services.sh to ensure services are healthy
- [x] 3.3 Start Django runserver with DEBUG=True and auto-reload
- [x] 3.4 Make script executable

## 4. Makefile

- [x] 4.1 Create Makefile with `dev` target (calls dev.sh or equivalent)
- [x] 4.2 Add `dev.up` target for Docker services only
- [x] 4.3 Add `dev.run` target for Django server only
- [x] 4.4 Add `test` target running pytest
- [x] 4.5 Add `lint` target running ruff, black, isort
- [x] 4.6 Add `clean` target removing __pycache__, .pyc, .pytest_cache

## 5. Environment configuration

- [x] 5.1 Create .env.development with DEBUG=True
- [x] 5.2 Set DATABASE_URL=postgres://fodejas_user:fodejas_password@localhost:5432/fodejas_db
- [x] 5.3 Set REDIS_URL=redis://localhost:6379/0
- [x] 5.4 Set CELERY_BROKER_URL=redis://localhost:6379/0
- [x] 5.5 Add .env.development to .gitignore

## 6. Docker Compose override

- [x] 6.1 Add healthcheck configuration to PostgreSQL service
- [x] 6.2 Add healthcheck configuration to Redis service
- [x] 6.3 Add healthcheck configuration to MinIO service
- [x] 6.4 Ensure depends_on uses condition: service_healthy
- [x] 6.5 Verify hot reload works with volume mount

## 7. Django settings updates

- [x] 7.1 Add DEBUG setting from environment variable with default True
- [x] 7.2 Configure development logging (DEBUG level, verbose format)
- [x] 7.3 Add INTERNAL_IPS for potential Django Debug Toolbar support

## 8. Documentation

- [x] 8.1 Update CONTRIBUTING.md with simplified setup using create_venv.sh and Makefile
- [x] 8.2 Document `make dev` as the primary development command
- [x] 8.3 Add troubleshooting section for common issues

## 9. Verification

- [x] 9.1 Run make lint and fix any issues
- [x] 9.2 Verify scripts are executable
- [x] 9.3 Verify all new files are ignored by .gitignore where appropriate
