## ADDED Requirements

### Requirement: Environment-specific .env.example files

The system SHALL provide `.env.<environment>.example` template files for development, staging, and production environments.

#### Scenario: Development environment template exists
- **WHEN** a developer clones the repository
- **THEN** a file `.env.development.example` SHALL exist in the project root
- **AND** it SHALL contain all variables needed for local development

#### Scenario: Staging environment template exists
- **WHEN** a deployer prepares staging deployment
- **THEN** a file `.env.staging.example` SHALL exist in the project root
- **AND** it SHALL mark sensitive values as `# REQUIRED:` with instructions

#### Scenario: Production environment template exists
- **WHEN** a deployer prepares production deployment
- **THEN** a file `.env.production.example` SHALL exist in the project root
- **AND** it SHALL mark all secrets as `# REQUIRED:` without placeholder values

### Requirement: Environment variable configuration

The system SHALL read configuration from environment variables following 12-factor app principles.

#### Scenario: Django reads DJANGO_ENV variable
- **WHEN** the application starts
- **THEN** it SHALL read `DJANGO_ENV` to determine the current environment
- **AND** valid values SHALL be: `development`, `staging`, `production`

#### Scenario: Required variables are validated
- **WHEN** `DJANGO_ENV` is set to `staging` or `production`
- **THEN** the system SHALL fail to start if required variables are missing
- **AND** the error message SHALL indicate which variable is missing

#### Scenario: DEBUG mode is tied to environment
- **WHEN** `DJANGO_ENV` is `production`
- **AND** `DEBUG` is `True`
- **THEN** the system SHALL refuse to start with a clear error message

### Requirement: Sensitive values excluded from version control

The system SHALL ensure no secrets are committed to the repository.

#### Scenario: .env files are gitignored
- **WHEN** a developer creates a `.env` file
- **THEN** it SHALL be ignored by git (not committed)
- **AND** only `.env.example` and `.env.<environment>.example` files SHALL be versioned

#### Scenario: .env.example contains no real secrets
- **WHEN** a `.env.<environment>.example` file is reviewed
- **THEN** no real passwords, API keys, or secrets SHALL be present
- **AND** sensitive fields SHALL be marked with `# REQUIRED:` or `# OPTIONAL:`

### Requirement: Configuration documentation

The system SHALL document all environment variables required for each environment.

#### Scenario: Variables are documented in .env.example
- **WHEN** a developer reads any `.env.example` file
- **THEN** each variable SHALL have a comment indicating if it is `REQUIRED` or `OPTIONAL`
- **AND** the purpose of the variable SHALL be clear from the comment

#### Scenario: Environment-specific README exists
- **WHEN** a new developer sets up the project
- **THEN** documentation SHALL explain how to create `.env` from `.env.<environment>.example`
