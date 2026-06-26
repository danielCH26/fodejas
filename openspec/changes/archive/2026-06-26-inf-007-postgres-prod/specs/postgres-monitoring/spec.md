## ADDED Requirements

### Requirement: Query performance tracking

The system SHALL track and expose slow query information using pg_stat_statements.

#### Scenario: Slow queries recorded
- **WHEN** a query exceeds the configured threshold (default 100ms)
- **THEN** it SHALL be recorded in pg_stat_statements
- **AND** SHALL be accessible via SQL view

#### Scenario: Top queries exposed
- **WHEN** querying pg_stat_statements
- **THEN** the top 10 slowest queries SHALL be viewable
- **AND** SHALL include call count, total time, and average time

### Requirement: Connection monitoring

The system SHALL expose PostgreSQL connection metrics.

#### Scenario: Active connections tracked
- **WHEN** monitoring system queries PostgreSQL
- **THEN** current connection count SHALL be exposed
- **AND** SHALL indicate if approaching max_connections limit

#### Scenario: PgBouncer pool stats exposed
- **WHEN** monitoring system queries PgBouncer admin
- **THEN** pool statistics SHALL be exposed
- **AND** SHALL include: total connections, idle connections, waiting clients

### Requirement: Cache hit ratio monitoring

The system SHALL track and expose buffer cache performance.

#### Scenario: Cache hit ratio calculated
- **WHEN** cache statistics are queried
- **THEN** buffer cache hit ratio SHALL be calculated
- **AND** SHALL be exposed as a metric

#### Scenario: Low cache hit ratio alert
- **WHEN** cache hit ratio falls below 90%
- **THEN** an alert SHALL be triggered
- **AND** SHALL indicate potential performance issue

### Requirement: Prometheus exporter compatibility

The system SHALL expose metrics in a format compatible with Prometheus scraping.

#### Scenario: Metrics endpoint available
- **WHEN** PostgreSQL is running
- **THEN** a metrics endpoint SHALL be available at `/metrics`
- **AND** SHALL return Prometheus text format

#### Scenario: Metrics include database stats
- **WHEN** `/metrics` is scraped
- **THEN** PostgreSQL metrics SHALL be included
- **AND** PgBouncer metrics SHALL be included if enabled
