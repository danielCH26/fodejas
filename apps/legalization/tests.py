"""Tests for the electronic signature service."""

import hashlib

import pytest

from apps.legalization.signer import (
    MockSigner,
    SignatureResult,
    SignerFactory,
    sign_document,
    verify_document,
)


class TestMockSigner:
    """Tests for MockSigner implementation."""

    def test_sign_returns_signature_result(self):
        """sign() should return a SignatureResult instance."""
        signer = MockSigner()
        doc = b"Test document"

        result = signer.sign(doc)

        assert isinstance(result, SignatureResult)
        assert result.pre_sign_hash is not None
        assert result.post_sign_hash is not None
        assert result.provider == "mock"

    def test_sign_generates_sha256_hashes(self):
        """sign() should generate SHA-256 hashes."""
        signer = MockSigner()
        doc = b"Test document"

        result = signer.sign(doc)

        # Verify SHA-256 format (64 hex characters)
        assert len(result.pre_sign_hash) == 64
        assert len(result.post_sign_hash) == 64

    def test_sign_deterministic_same_input(self):
        """sign() with same input should return same pre-sign hash."""
        signer = MockSigner()
        doc = b"Test document"

        result1 = signer.sign(doc)
        result2 = signer.sign(doc)

        assert result1.pre_sign_hash == result2.pre_sign_hash

    def test_sign_different_inputs_different_hashes(self):
        """sign() with different inputs should return different hashes."""
        signer = MockSigner()

        result1 = signer.sign(b"Document 1")
        result2 = signer.sign(b"Document 2")

        assert result1.pre_sign_hash != result2.pre_sign_hash

    def test_sign_includes_metadata(self):
        """sign() should include metadata in result."""
        signer = MockSigner()
        doc = b"Test document"

        result = signer.sign(doc)

        assert "provider" in result.metadata
        assert "algorithm" in result.metadata
        assert "timestamp" in result.metadata
        assert result.metadata["algorithm"] == "SHA-256"

    def test_verify_returns_true_for_matching_hash(self):
        """verify() should return True when hashes match."""
        signer = MockSigner()
        doc = b"Test document"
        expected_hash = hashlib.sha256(doc).hexdigest()

        result = signer.verify(doc, expected_hash)

        assert result is True

    def test_verify_returns_false_for_mismatching_hash(self):
        """verify() should return False when hashes don't match."""
        signer = MockSigner()
        doc = b"Test document"

        result = signer.verify(doc, "invalid_hash")

        assert result is False


class TestSignerFactory:
    """Tests for SignerFactory."""

    def test_get_default_provider(self):
        """get_provider() without args should return default provider."""
        signer = SignerFactory.get_provider()

        assert isinstance(signer, MockSigner)

    def test_get_mock_provider_by_name(self):
        """get_provider('mock') should return MockSigner."""
        signer = SignerFactory.get_provider("mock")

        assert isinstance(signer, MockSigner)

    def test_get_provider_raises_for_unknown(self):
        """get_provider() should raise ValueError for unknown provider."""
        with pytest.raises(ValueError, match="Unknown signature provider"):
            SignerFactory.get_provider("nonexistent")


class TestConvenienceFunctions:
    """Tests for sign_document and verify_document."""

    def test_sign_document_creates_signature(self):
        """sign_document() should create a valid signature."""
        doc = b"Test document"

        result = sign_document(doc, "test_doc")

        assert isinstance(result, SignatureResult)
        assert result.pre_sign_hash is not None

    def test_sign_document_accepts_document_type(self):
        """sign_document() should accept document_type parameter."""
        doc = b"Test document"

        result = sign_document(doc, "promissory_note")

        assert result.provider == "mock"

    def test_sign_document_without_audit(self):
        """sign_document() should work without audit logging."""
        doc = b"Test document"

        result = sign_document(doc, "test", log_audit=False)

        assert isinstance(result, SignatureResult)

    def test_verify_document_returns_bool(self):
        """verify_document() should return boolean."""
        doc = b"Test document"
        expected_hash = hashlib.sha256(doc).hexdigest()

        result = verify_document(doc, expected_hash)

        assert isinstance(result, bool)
        assert result is True
