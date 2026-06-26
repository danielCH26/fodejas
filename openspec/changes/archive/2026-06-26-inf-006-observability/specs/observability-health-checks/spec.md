## ADDED Requirements

### Requirement: Liveness probe endpoint

The system SHALL provide a `/healthz` endpoint that returns 200 if the Django process is alive.

#### Scenario: Liveness returns 200 when healthy
- **WHEN** GET request is made to `/healthz`
- **THEN** the response SHALL be HTTP 200
- **AND** the response body SHALL be `{"status": "ok"}`
- **AND** the response SHALL include `Content-Type: application/json`

#### Scenario: Liveness does not check dependencies
- **WHEN** GET request is made to `/healthz`
- **AND** database is unavailable
- **THEN** the response SHALL still be HTTP 200
- **AND** the response SHALL indicate the process is alive

### Requirement: Readiness probe endpoint

The system SHALL provide a `/readyz` endpoint that verifies critical dependencies.

#### Scenario: Readiness returns 200 when all dependencies healthy
- **WHEN** GET request is made to `/readyz`
- **AND** database is reachable
- **AND** Redis is reachable
- **AND** Sentry SDK is configured
- **THEN** the response SHALL be HTTP 200
- **AND** the response body SHALL list each dependency with status

#### Scenario: Readiness returns 503 when dependency fails
- **WHEN** GET request is made to `/readyz`
- **AND** any critical dependency is unavailable
- **THEN** the response SHALL be HTTP 503
- **AND** the response body SHALL indicate which dependency failed

### Requirement: Health check timeout

The system SHALL timeout readiness checks to prevent blocking.

#### Scenario: Readiness timeout after 5 seconds
- **WHEN** GET request is made to `/readyz`
- **AND** a dependency check takes longer than 5 seconds
- **THEN** the check SHALL be aborted
- **AND** the response SHALL be HTTP 503
- **AND** the response SHALL indicate timeout

### Requirement: Health endpoints are unauthenticated

The system SHALL allow health checks without authentication.

#### Scenario: Health endpoints accessible without auth
- **WHEN** GET request is made to `/healthz` or `/readyz`
- **THEN** no authentication SHALL be required
- **AND** no session SHALL be created
