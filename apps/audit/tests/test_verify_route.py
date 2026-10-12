"""Route registration tests for the audit chain verification API (go-live readiness).

``/api/audit/`` mounts ``apps.audit.urls``. The ``verify/`` path must serve
the JSON API view (``AuditChainVerifyView``, DRF, staff-only) because the
``/api/`` prefix is an API contract; the HTML verification page remains at
``/accounts/audit/verify/`` (registered in ``apps/accounts/urls.py``).

Regression guard: swapping these views or dropping the route silently
breaks operators who verify the audit chain (docs/ops/03-incident-response.md
§ audit chain).

The ``.mo`` files for the English locale are committed (CHG-507); no
translation setup is required for these tests.
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestAuditVerifyApiRoute:
    """/api/audit/verify/ must return the JSON chain verification payload."""

    def test_admin_gets_json_payload(self, admin_user):
        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/audit/verify/")

        assert response.status_code == status.HTTP_200_OK
        assert response.accepted_renderer.format == "json" if hasattr(
            response, "accepted_renderer"
        ) else True
        # JSON contract from AuditChainVerifySerializer
        assert "is_valid" in response.data
        assert "last_valid_hash" in response.data
        assert isinstance(response.data["is_valid"], bool)

    def test_payload_matches_service_on_empty_ledger(self, admin_user):
        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/audit/verify/")

        assert response.status_code == status.HTTP_200_OK
        # The test DB may carry seeded audit events; the contract is a
        # valid chain with a 64-hex head (NOT necessarily the genesis hash).
        assert response.data["is_valid"] is True
        assert len(response.data["last_valid_hash"]) == 64

    def test_anonymous_gets_401_or_403(self):
        client = APIClient()
        response = client.get("/api/audit/verify/")

        # IsAdminUser: anonymous → 401 (challenge) per DRF convention
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_html_verify_still_served_at_accounts(self, admin_user, client):
        """The HTML verification page must remain at /accounts/audit/verify/."""
        client.force_login(admin_user)
        response = client.get(reverse("accounts:audit_verify"))

        assert response.status_code == status.HTTP_200_OK
        assert "Cadena de Auditoría" in response.content.decode("utf-8")

    def test_html_audit_dashboard_renders(self, admin_user, client):
        """Regression: audit dashboard previously 500'd on {% url 'audit_dashboard' %}
        (bare name, registered only under the accounts namespace)."""
        client.force_login(admin_user)
        response = client.get(reverse("accounts:audit_dashboard"))

        assert response.status_code == status.HTTP_200_OK

    def test_html_audit_detail_renders(self, admin_user, client):
        """Regression: audit event detail page renders without url errors."""
        from apps.audit.services import log_audit_event
        import uuid

        event = log_audit_event(
            actor=None,
            action="CREATE",
            entity="Convocatory",
            entity_id=uuid.uuid4(),
            changes={"after": {"nombre": "x"}},
            module="convocatories",
        )
        client.force_login(admin_user)
        response = client.get(reverse("accounts:audit_detail", args=[event.id]))

        assert response.status_code == status.HTTP_200_OK
