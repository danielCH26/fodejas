## 1. Core Secrets Module

- [x] 1.1 Create `apps/core/secrets.py` with `SecretsError` base exception
- [x] 1.2 Create `MissingSecretError` exception class
- [x] 1.3 Create abstract `SecretStore` class with `get`, `get_required`, `list_keys` methods
- [x] 1.4 Create `EnvSecretStore` implementation

## 2. Django Settings Integration

- [x] 2.1 Update `config/settings.py` to use `EnvSecretStore` for secrets retrieval
- [x] 2.2 Replace direct `environ` calls with `secrets.get_required()`
- [x] 2.3 Add validation at startup for required secrets

## 3. Pre-commit Configuration

- [x] 3.1 Create `.pre-commit-config.yaml` with `detect-secrets` hook
- [x] 3.2 Configure `detect-secrets` baseline file
- [x] 3.3 Create initial `.secrets.baseline` with development secrets allowlisted
- [x] 3.4 Add pre-commit installation to `scripts/setup.sh`

## 4. CI/CD Integration

- [x] 4.1 Add `detect-secrets` scan job to `ci.yml`
- [x] 4.2 Configure CI to fail if new secrets are detected

## 5. Documentation

- [x] 5.1 Add secrets management section to CONTRIBUTING.md
- [x] 5.2 Document rotation policy and procedures
- [x] 5.3 Add troubleshooting section for common secret issues

## 6. Testing

- [x] 6.1 Create `apps/core/tests/test_secrets.py`
- [x] 6.2 Write tests for `EnvSecretStore.get`
- [x] 6.3 Write tests for `EnvSecretStore.get_required` with missing key
- [x] 6.4 Write tests for `MissingSecretError` exception
