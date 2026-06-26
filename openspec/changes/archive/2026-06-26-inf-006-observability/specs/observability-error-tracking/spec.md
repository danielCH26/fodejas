## ADDED Requirements

### Requirement: Sentry integration

The system SHALL send unhandled exceptions to Sentry when `DJANGO_ENV` is `staging` or `production`.

#### Scenario: Unhandled exception sent to Sentry
- **WHEN** an unhandled exception occurs during request processing
- **THEN** the exception SHALL be sent to Sentry
- **AND** the event SHALL include request context (method, path, user agent)
- **AND** the event SHALL include authenticated user ID if available

#### Scenario: Celery task exception sent to Sentry
- **WHEN** an unhandled exception occurs in a Celery task
- **THEN** the exception SHALL be sent to Sentry
- **AND** the event SHALL include task name and task ID

### Requirement: Sentry context enrichment

The system SHALL enrich Sentry events with additional context.

#### Scenario: User context attached
- **WHEN** an exception occurs for an authenticated user
- **THEN** Sentry SHALL display the user ID in the event
- **AND** user email SHALL NOT be sent (PII protection)

#### Scenario: Request context attached
- **WHEN** an exception occurs during HTTP request processing
- **THEN** Sentry SHALL include: HTTP method, URL path, query string (without secrets), client IP

### Requirement: Sentry performance tracking disabled

The system SHALL NOT enable Sentry performance tracing to avoid overhead.

#### Scenario: Performance monitoring inactive
- **WHEN** Sentry SDK is configured
- **THEN** performance monitoring SHALL be disabled
- **AND** only error tracking SHALL be active

### Requirement: Sensitive data not sent to Sentry

The system SHALL prevent sensitive data from being sent to Sentry.

#### Scenario: Passwords not sent
- **WHEN** logging request data for Sentry
- **THEN** fields matching `password`, `secret`, `token`, `authorization` SHALL be redacted
- **AND** request bodies SHALL be excluded from Sentry events
