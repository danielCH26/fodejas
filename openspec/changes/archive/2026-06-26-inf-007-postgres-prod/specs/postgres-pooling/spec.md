## ADDED Requirements

### Requirement: PgBouncer connection pooling

The system SHALL use PgBouncer as a connection pooler between Django and PostgreSQL in production.

#### Scenario: PgBouncer runs as separate service
- **WHEN** the application starts in production
- **THEN** PgBouncer SHALL run as a separate Docker service
- **AND** Django SHALL connect to PgBouncer instead of PostgreSQL directly

#### Scenario: Transaction pooling mode
- **WHEN** PgBouncer is configured
- **THEN** pooling mode SHALL be set to `transaction`
- **AND** prepared statements SHALL be disabled

#### Scenario: Connection limits configured
- **WHEN** PgBouncer starts
- **THEN** `max_client_conn` SHALL be set to 100
- **AND** `default_pool_size` SHALL be set to 20
- **AND** `reserve_pool_size` SHALL be set to 5

### Requirement: Connection string compatibility

The system SHALL maintain compatibility with Django's database connection handling.

#### Scenario: Django connects through PgBouncer
- **WHEN** `DJANGO_ENV` is `production`
- **THEN** DATABASE_URL SHALL point to `pgbouncer:6432`
- **AND** Django SHALL be able to connect without issues

#### Scenario: Health check endpoint
- **WHEN** a health check request is made to PgBouncer
- **THEN** PgBouncer SHALL respond on its admin interface
- **AND** SHALL indicate pooler status

### Requirement: Graceful degradation

The system SHALL fall back to direct PostgreSQL connection if PgBouncer is unavailable.

#### Scenario: PgBouncer unavailable
- **WHEN** PgBouncer service is down
- **THEN** application SHALL be able to connect directly to PostgreSQL
- **AND** DATABASE_URL fallback SHALL be documented

#### Scenario: Connection timeout configured
- **WHEN** PgBouncer is overloaded
- **THEN** connection attempts SHALL timeout after configured period
- **AND** SHALL return appropriate error to application
