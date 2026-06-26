## ADDED Requirements

### Requirement: Prometheus metrics endpoint

The system SHALL expose metrics in Prometheus format at `/metrics`.

#### Scenario: Metrics endpoint returns Prometheus format
- **WHEN** GET request is made to `/metrics`
- **THEN** the response SHALL be Prometheus text format
- **AND** the response SHALL include `Content-Type: text/plain; version=0.0.4`

#### Scenario: Metrics endpoint includes Django metrics
- **WHEN** GET request is made to `/metrics`
- **THEN** the response SHALL include `django_http_requests_total` by view and status
- **AND** the response SHALL include `django_http_request_duration_seconds` by view

### Requirement: Celery task metrics

The system SHALL export Celery task metrics.

#### Scenario: Celery task count metric
- **WHEN** a Celery task completes
- **THEN** `celery_tasks_total` counter SHALL be incremented
- **AND** the metric SHALL include labels: `task_name`, `status` (success/failure)

#### Scenario: Celery task latency metric
- **WHEN** a Celery task completes
- **THEN** `celery_task_latency_seconds` histogram SHALL record the duration
- **AND** the metric SHALL include labels: `task_name`

### Requirement: Metrics are internal

The `/metrics` endpoint SHALL only be accessible internally.

#### Scenario: Metrics endpoint not publicly exposed
- **WHEN** `/metrics` is accessed
- **THEN** it SHALL be accessible from internal network only
- **AND** documentation SHALL note it requires network-level protection

### Requirement: Metrics collection is low-overhead

The system SHALL minimize performance impact from metrics collection.

#### Scenario: Metrics collection does not block requests
- **WHEN** Django processes a request
- **THEN** metrics collection SHALL be non-blocking
- **AND** metrics SHALL be collected asynchronously
