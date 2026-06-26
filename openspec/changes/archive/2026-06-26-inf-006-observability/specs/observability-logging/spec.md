## ADDED Requirements

### Requirement: JSON structured logging

The system SHALL log in JSON format when `DJANGO_ENV` is `staging` or `production`.

#### Scenario: JSON logs in production
- **WHEN** Django logs an event in production
- **THEN** the output SHALL be a valid JSON object per line
- **AND** each log entry SHALL contain `timestamp`, `level`, `message`, `module`, `process`, `thread`

#### Scenario: Human-readable logs in development
- **WHEN** Django logs an event in development
- **THEN** the output SHALL be human-readable text format

### Requirement: Request ID correlation

The system SHALL generate and propagate a unique request ID for every HTTP request.

#### Scenario: Request ID generated for each request
- **WHEN** an HTTP request arrives without `X-Request-ID` header
- **THEN** the system SHALL generate a UUID4 as the request ID
- **AND** the request ID SHALL be included in all log entries for that request

#### Scenario: Request ID propagated from header
- **WHEN** an HTTP request arrives with `X-Request-ID` header
- **THEN** the system SHALL use that value as the request ID
- **AND** the request ID SHALL be included in all log entries for that request

#### Scenario: Request ID returned in response
- **WHEN** an HTTP request is processed
- **THEN** the response SHALL include `X-Request-ID` header with the request ID

### Requirement: Log fields for security

The system SHALL include security-relevant fields in logs without exposing sensitive data.

#### Scenario: User ID logged without PII
- **WHEN** a request is authenticated
- **THEN** the user ID (not email, not name) SHALL be logged in the `user_id` field
- **AND** personal information SHALL NOT be logged

#### Scenario: Sensitive paths not logged
- **WHEN** a request is made to a path containing `password` or `token`
- **THEN** the path SHALL be logged as `[REDACTED]`
- **AND** query parameters SHALL be logged as `[REDACTED]`

### Requirement: Async logging

The system SHALL use non-blocking log handlers to avoid impacting request latency.

#### Scenario: Logging does not block requests
- **WHEN** Django logs an event
- **THEN** the logging operation SHALL not block the request thread
- **AND** logs SHALL be written via a background queue
