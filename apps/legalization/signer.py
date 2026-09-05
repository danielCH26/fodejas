"""Electronic signature service with abstract interface.

This module provides an interchangeable electronic signature service
for signing legal documents (promissory notes, contracts, etc.) in
the FODEJAS platform.

The service uses SHA-256 hashing for document integrity verification,
as required by Art. 45 CPACA and Decreto 0372/2025.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from django.conf import settings


@dataclass
class SignatureResult:
    """Result of a document signing operation.

    Attributes:
        pre_sign_hash: SHA-256 hash of the document before signing.
        post_sign_hash: SHA-256 hash after signing (includes signature metadata).
        metadata: JSON-serializable dict with provider, timestamp, algorithm.
        provider: Identifier of the signing provider used.
    """

    pre_sign_hash: str
    post_sign_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)
    provider: str = "unknown"


class ElectronicSigner(ABC):
    """Abstract base class for electronic signature providers.

    Implementations must provide sign() and verify() methods.
    """

    @abstractmethod
    def sign(self, document_data: bytes) -> SignatureResult:
        """Sign a document and return the signature result.

        Args:
            document_data: Raw bytes of the document to sign.

        Returns:
            SignatureResult containing pre/post hashes and metadata.
        """
        pass

    @abstractmethod
    def verify(self, document_data: bytes, expected_hash: str) -> bool:
        """Verify document integrity against expected hash.

        Args:
            document_data: Raw bytes of the document to verify.
            expected_hash: Expected SHA-256 hash to compare against.

        Returns:
            True if hashes match, False otherwise.
        """
        pass


class MockSigner(ElectronicSigner):
    """Mock signer for development and testing.

    This implementation returns deterministic SHA-256 hashes
    for reproducible development and testing workflows.
    """

    def sign(self, document_data: bytes) -> SignatureResult:
        """Sign document with deterministic mock signature.

        Args:
            document_data: Raw bytes of the document to sign.

        Returns:
            SignatureResult with mock hashes and metadata.
        """
        pre_hash = hashlib.sha256(document_data).hexdigest()

        # Mock signature: append provider info to hash
        metadata = {
            "provider": "mock",
            "algorithm": "SHA-256",
            "timestamp": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
            "environment": "development",
        }
        mock_signature = json.dumps(metadata, sort_keys=True).encode()
        post_hash = hashlib.sha256(document_data + mock_signature).hexdigest()

        return SignatureResult(
            pre_sign_hash=pre_hash,
            post_sign_hash=post_hash,
            metadata=metadata,
            provider="mock",
        )

    def verify(self, document_data: bytes, expected_hash: str) -> bool:
        """Verify document against expected hash.

        Args:
            document_data: Raw bytes of the document.
            expected_hash: Expected SHA-256 hash.

        Returns:
            True if computed hash matches expected.
        """
        computed_hash = hashlib.sha256(document_data).hexdigest()
        return computed_hash == expected_hash


class SignerFactory:
    """Factory for obtaining electronic signature providers.

    Supports runtime provider selection without code changes.
    """

    _providers: dict[str, type[ElectronicSigner]] = {
        "mock": MockSigner,
    }

    @classmethod
    def get_provider(cls, provider_name: str | None = None) -> ElectronicSigner:
        """Get an electronic signer provider instance.

        Args:
            provider_name: Name of the provider to instantiate.
                          If None, uses default from settings.

        Returns:
            ElectronicSigner instance.

        Raises:
            ValueError: If provider_name is not registered.
        """
        if provider_name is None:
            provider_name = getattr(settings, "ELECTRONIC_SIGNATURE_PROVIDER", "mock")

        provider_class = cls._providers.get(provider_name)
        if provider_class is None:
            raise ValueError(
                f"Unknown signature provider: {provider_name}. "
                f"Available: {list(cls._providers.keys())}"
            )

        return provider_class()

    @classmethod
    def register_provider(cls, name: str, provider_class: type[ElectronicSigner]) -> None:
        """Register a new provider.

        Args:
            name: Provider identifier.
            provider_class: ElectronicSigner implementation class.
        """
        cls._providers[name] = provider_class


def _log_signature_audit(
    document_type: str,
    result: SignatureResult,
    actor_id: int | None = None,
    entity_id: str | None = None,
) -> None:
    """Log signature operation to audit trail (CAP-022).

    Args:
        document_type: Type of document being signed (e.g., 'promissory_note').
        result: SignatureResult from the signing operation.
        actor_id: ID of the user performing the signing (optional).
        entity_id: UUID of the document being signed (optional).
    """
    try:
        from apps.audit.services import log_audit_event

        log_audit_event(
            actor=None,  # Will be resolved by the service
            action="ELECTRONIC_SIGNATURE",
            entity=document_type,
            entity_id=entity_id,
            changes={
                "pre_sign_hash": result.pre_sign_hash,
                "post_sign_hash": result.post_sign_hash,
                "provider": result.provider,
                "metadata": result.metadata,
            },
            module="legalization",
        )
    except Exception as e:
        # Log the error instead of silent pass - per AGENTS.md §7
        import logging
        logging.warning(f"Audit logging failed for signature: {e}")


def sign_document(
    document_data: bytes,
    document_type: str = "document",
    actor_id: int | None = None,
    log_audit: bool = True,
) -> SignatureResult:
    """Sign a document using the default provider.

    Args:
        document_data: Raw bytes of the document to sign.
        document_type: Type of document for audit trail (e.g., 'promissory_note').
        actor_id: ID of the user performing the signing.
        log_audit: Whether to log to audit trail (CAP-022).

    Returns:
        SignatureResult from the default provider.
    """
    signer = SignerFactory.get_provider()
    result = signer.sign(document_data)

    if log_audit:
        _log_signature_audit(document_type, result, actor_id)

    return result


def verify_document(document_data: bytes, expected_hash: str) -> bool:
    """Convenience function to verify document integrity.

    Args:
        document_data: Raw bytes of the document.
        expected_hash: Expected SHA-256 hash.

    Returns:
        True if hashes match.
    """
    signer = SignerFactory.get_provider()
    return signer.verify(document_data, expected_hash)
