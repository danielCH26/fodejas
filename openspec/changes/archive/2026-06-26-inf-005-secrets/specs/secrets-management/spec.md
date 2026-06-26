## ADDED Requirements

### Requirement: SecretStore abstract interface

The system SHALL provide an abstract `SecretStore` class that defines the interface for retrieving secrets from any backing store.

#### Scenario: SecretStore subclass must implement get method
- **WHEN** a subclass of `SecretStore` is created
- **THEN** it SHALL implement the `get(key: str) -> str` method

#### Scenario: SecretStore subclass must implement get_required method
- **WHEN** a subclass of `SecretStore` is created
- **THEN** it SHALL implement the `get_required(key: str) -> str` method
- **AND** it SHALL raise `MissingSecretError` when the secret is not found

#### Scenario: SecretStore subclass must implement list_keys method
- **WHEN** a subclass of `SecretStore` is created
- **THEN** it SHALL implement the `list_keys() -> list[str]` method

### Requirement: EnvSecretStore implementation

The system SHALL provide `EnvSecretStore` that retrieves secrets from environment variables.

#### Scenario: EnvSecretStore returns environment variable value
- **WHEN** `EnvSecretStore.get("SECRET_KEY")` is called
- **AND** the environment variable `SECRET_KEY` is set to `"abc123"`
- **THEN** it SHALL return `"abc123"`

#### Scenario: EnvSecretStore returns None for missing variable
- **WHEN** `EnvSecretStore.get("NONEXISTENT_VAR")` is called
- **AND** the environment variable does not exist
- **THEN** it SHALL return `None`

#### Scenario: EnvSecretStore raises for missing required variable
- **WHEN** `EnvSecretStore.get_required("NONEXISTENT_VAR")` is called
- **AND** the environment variable does not exist
- **THEN** it SHALL raise `MissingSecretError` with message containing the key name

#### Scenario: EnvSecretStore lists all environment variable keys
- **WHEN** `EnvSecretStore.list_keys()` is called
- **THEN** it SHALL return a list of all environment variable names that match the secrets prefix pattern

### Requirement: Secrets detection in pre-commit

The system SHALL use `detect-secrets` to prevent secrets from being committed to the repository.

#### Scenario: Pre-commit hook detects potential secret
- **WHEN** a developer runs `git commit` with a file containing a potential secret
- **AND** the secret is not in the baseline allowlist
- **THEN** the commit SHALL be blocked
- **AND** the hook SHALL output a warning with the file and line number

#### Scenario: Pre-commit hook allows baseline secrets
- **WHEN** a developer runs `git commit` with a file containing a secret
- **AND** the secret is explicitly allowlisted in `.secrets.baseline`
- **THEN** the commit SHALL proceed

### Requirement: CI/CD secret validation

The system SHALL run a CI job to verify no untracked secrets exist in the repository.

#### Scenario: CI fails when new secret is committed
- **WHEN** a commit introduces a new secret not in the baseline
- **AND** CI runs the `detect-secrets` scan
- **THEN** the CI job SHALL fail

### Requirement: MissingSecretError exception

The system SHALL provide a `MissingSecretError` exception for when required secrets are not found.

#### Scenario: MissingSecretError contains key information
- **WHEN** `MissingSecretError` is raised
- **THEN** the exception message SHALL contain the key name that was missing
- **AND** the exception SHALL be catchable as `SecretsError` base class
