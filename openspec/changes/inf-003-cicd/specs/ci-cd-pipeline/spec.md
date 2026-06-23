## ADDED Requirements

### Requirement: CI workflow for lint

The system SHALL provide a GitHub Actions workflow that runs linting tools (ruff, black, isort) on every push and pull request to `main` and `develop` branches.

### Requirement: CI workflow for tests

The system SHALL provide a GitHub Actions workflow that runs pytest on every push and pull request to `main` and `develop` branches.

**Exception:** During the initial project phase when no tests exist, the test job SHALL NOT fail the pipeline. Linting SHALL always be mandatory.

#### Scenario: Tests are optional during initial phase
- **WHEN** the test job runs and no test files exist
- **THEN** the system SHALL skip tests with a message "No tests found, skipping..."
- **AND** the job SHALL report success

#### Scenario: CI runs sequentially
- **WHEN** a push or PR triggers CI
- **THEN** the lint job SHALL run first
- **AND** the test job SHALL run only after lint passes (using `needs: lint`)

### Requirement: Docker image build

The system SHALL provide a GitHub Actions workflow that builds a multi-stage Docker image and pushes it to Docker Hub (`docker.io/danielch26/fodejas`) on merge to `develop` (staging) and `main` (production).

#### Scenario: Multi-stage production build
- **WHEN** the Docker image is built
- **THEN** the system SHALL use a multi-stage Dockerfile
- **AND** production image SHALL NOT include development dependencies

#### Scenario: Docker Hub authentication
- **WHEN** pushing images to Docker Hub
- **THEN** the system SHALL authenticate using tokens from GitHub Environment Secrets
- **AND** staging environment SHALL use `DOCKER_TOKEN_STAGING`
- **AND** production environment SHALL use `DOCKER_TOKEN_PRODUCTION`

### Requirement: Docker registry authentication

The system SHALL authenticate to Docker Hub using tokens stored as GitHub Environment Secrets.

#### Scenario: Token-based authentication
- **WHEN** pushing images to Docker Hub
- **THEN** the system SHALL use `DOCKER_TOKEN_STAGING` for staging environment
- **AND** `DOCKER_TOKEN_PRODUCTION` for production environment
- **AND** tokens SHALL have appropriate scopes (packages:read, packages:write)

### Requirement: Service availability check

The system SHALL wait for PostgreSQL and Redis to be available before starting the Django application.

#### Scenario: Wait for PostgreSQL
- **WHEN** the container starts
- **THEN** the system SHALL wait for PostgreSQL using `pg_isready`
- **AND** SHALL retry until available or timeout (60 seconds)

#### Scenario: Wait for Redis
- **WHEN** the container starts
- **THEN** the system SHALL wait for Redis using `redis-cli ping`
- **AND** SHALL retry until available or timeout (30 seconds)

#### Scenario: Service unavailable after timeout
- **WHEN** a service is not available after timeout
- **THEN** the container SHALL fail with a clear error message

### Requirement: Docker Compose health checks

The system SHALL provide Docker Compose configuration with health checks for PostgreSQL and Redis services.

#### Scenario: Health check configuration
- **WHEN** running with docker-compose
- **THEN** PostgreSQL healthcheck SHALL use `pg_isready`
- **AND** Redis healthcheck SHALL use `redis-cli ping`
- **AND** app service SHALL use `depends_on` with `condition: service_healthy`

### Requirement: Staging deployment workflow

The system SHALL provide a GitHub Actions workflow for staging deployment that serves as orchestration placeholder.

#### Scenario: Staging deployment orchestration
- **WHEN** user triggers workflow dispatch on staging workflow
- **THEN** the workflow SHALL display deployment information
- **AND** SHALL require the `staging` GitHub Environment
- **AND** actual server deployment requires external infrastructure configuration

**Note:** This workflow is a deployment orchestration placeholder. Actual deployment to staging server requires additional infrastructure (server, Docker Compose configuration, etc.) that is outside the scope of this change.

### Requirement: Production deployment workflow

The system SHALL provide a GitHub Actions workflow for production deployment via manual workflow dispatch.

#### Scenario: Manual deploy to production
- **WHEN** user triggers workflow dispatch on production workflow
- **AND** selects a valid image tag
- **THEN** the workflow SHALL display deployment information
- **AND** SHALL require the `production` GitHub Environment with at least 1 reviewer

**Note:** This workflow is a deployment orchestration placeholder. Actual deployment to production server requires additional infrastructure that is outside the scope of this change.

### Requirement: Branch protection

The system SHALL enforce branch protection rules on `main` and `develop` branches requiring pull requests and passing status checks before merge.

#### Scenario: PR cannot merge without passing checks
- **WHEN** a pull request targets `main` or `develop`
- **AND** CI checks (lint or tests) are failing
- **THEN** the system SHALL block the merge

### Requirement: GitHub Environments

The system SHALL use GitHub Environments with protection rules for staging and production deployments.

#### Scenario: Production environment requires reviewers
- **WHEN** deploying to production
- **THEN** at least 1 reviewer SHALL be required
- **AND** secrets SHALL be per-environment

### Requirement: CI badges

The system SHALL display CI/CD status badges in the README.md file for lint and test workflows.

#### Scenario: Badge reflects current status
- **WHEN** the README is viewed
- **THEN** the badge SHALL show the current status of the default branch (passing/failing)
