import os
from abc import ABC, abstractmethod


class SecretsError(Exception):
    pass


class MissingSecretError(SecretsError):
    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Required secret '{key}' is not set")


class SecretStore(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def get_required(self, key: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_keys(self) -> list[str]:
        raise NotImplementedError


class EnvSecretStore(SecretStore):
    def get(self, key: str) -> str | None:
        return os.environ.get(key)

    def get_required(self, key: str) -> str:
        value = self.get(key)
        if value is None:
            raise MissingSecretError(key)
        return value

    def list_keys(self) -> list[str]:
        return list(os.environ.keys())


secrets = EnvSecretStore()
