import os

import pytest

from apps.core.secrets import EnvSecretStore, MissingSecretError, SecretsError


class TestSecretsError:
    def test_missing_secret_error_contains_key(self):
        error = MissingSecretError("TEST_KEY")
        assert error.key == "TEST_KEY"
        assert "TEST_KEY" in str(error)

    def test_missing_secret_error_is_catchable_as_secrets_error(self):
        with pytest.raises(SecretsError):
            raise MissingSecretError("TEST_KEY")


class TestEnvSecretStore:
    def setup_method(self):
        self.store = EnvSecretStore()
        os.environ["TEST_SECRET"] = "test_value"
        os.environ["EMPTY_SECRET"] = ""

    def teardown_method(self):
        if "TEST_SECRET" in os.environ:
            del os.environ["TEST_SECRET"]
        if "EMPTY_SECRET" in os.environ:
            del os.environ["EMPTY_SECRET"]
        if "NONEXISTENT_VAR" in os.environ:
            del os.environ["NONEXISTENT_VAR"]

    def test_get_returns_value(self):
        result = self.store.get("TEST_SECRET")
        assert result == "test_value"

    def test_get_returns_none_for_missing(self):
        result = self.store.get("NONEXISTENT_VAR")
        assert result is None

    def test_get_returns_empty_string(self):
        result = self.store.get("EMPTY_SECRET")
        assert result == ""

    def test_get_required_returns_value(self):
        result = self.store.get_required("TEST_SECRET")
        assert result == "test_value"

    def test_get_required_raises_for_missing(self):
        with pytest.raises(MissingSecretError) as exc_info:
            self.store.get_required("NONEXISTENT_VAR")
        assert exc_info.value.key == "NONEXISTENT_VAR"

    def test_list_keys_returns_list(self):
        keys = self.store.list_keys()
        assert isinstance(keys, list)
        assert "TEST_SECRET" in keys
