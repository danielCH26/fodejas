"""Tests for retorno_archipelago annotation endpoint (CHG-506, CAP-027).

All fixtures use synthetic data only (AGENTS.md §6.1 — no PII).
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.academic_tracking.models import AcademicRecord
from apps.accounts.models import Role
from apps.accounts.services.assignment import assign_role_to_user
from apps.accounts.services.sync import sync_role_to_group
from apps.audit.models import AuditEvent
from apps.convocatories.models import Convocatory
from apps.legalization.models import LegalizationProcess

User = get_user_model()


def _make_role(code):
    role, _ = Role.objects.get_or_create(
        code=code,
        defaults={"name": code, "type": "interno", "description": code},
    )
    sync_role_to_group(role)
    return role


def _make_user(n, roles=None):
    user = User.objects.create_user(
        email=f"synthetic-ret-{n}@example.test",
        documento=f"1122334{n:04d}",
        password="test-password-not-real",
        first_name="Retorno",
        last_name="Test",
        is_staff=bool(roles),
        is_superuser=bool(roles),
    )
    for code in roles or []:
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={"name": code, "type": "interno", "description": code},
        )
        sync_role_to_group(role)
        assign_role_to_user(user, role)
    return user


def _make_record(n):
    beneficiary = _make_user(200 + n)
    conv = Convocatory.objects.create(
        codigo=f"CHG-506-RET-{n}",
        nombre=f"Conv Retorno {n}",
        estado=Convocatory.Estado.PUBLICADA,
        periodo=f"2023-1",
    )
    process = LegalizationProcess.objects.create(
        beneficiary=beneficiary,
        convocatoria=conv,
        status=LegalizationProcess.Status.LEGALIZADO,
    )
    return AcademicRecord.objects.create(
        legalization_process=process,
        status=AcademicRecord.Status.ACTIVO,
    )


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAnotarRetornoAPI:
    """RED: action does not exist yet → 404."""

    def _url(self, pk):
        return f"/api/academic-tracking/records/{pk}/anotar_retorno/"

    def _patch(self, user, record_pk, value, format="json"):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.patch(self._url(record_pk), {"retorno_archipelago": value}, format=format)

    def test_coord_patch_true_200(self, db):
        """R-COORD with retorno_archipelago=true → 200."""
        user = _make_user(1, roles=["R-COORD"])
        record = _make_record(1)
        response = self._patch(user, record.id, True)
        assert response.status_code == 200
        assert response.data["retorno_archipelago"] is True

    def test_coord_patch_false_200(self, db):
        """R-COORD with retorno_archipelago=false → 200."""
        user = _make_user(2, roles=["R-COORD"])
        record = _make_record(2)
        response = self._patch(user, record.id, False)
        assert response.status_code == 200
        assert response.data["retorno_archipelago"] is False

    def test_admin_patch_true_200(self, db):
        """R-ADMIN → 200."""
        user = _make_user(3, roles=["R-ADMIN"])
        record = _make_record(3)
        response = self._patch(user, record.id, True)
        assert response.status_code == 200

    def test_sin_rol_403(self, db):
        """User without R-COORD or R-ADMIN → 403."""
        user = _make_user(10)
        record = _make_record(10)
        response = self._patch(user, record.id, True)
        assert response.status_code == 403

    def test_r_ct_403_no_permiso_escritura(self, db):
        """R-CT has no write access to academic_tracking → 403.

        Note: _make_user with roles sets is_superuser=True which bypasses
        _AcademicManagementPermission. We create the user manually without
        superuser/staff flags to test the actual role-based permission.
        """
        user = User.objects.create_user(
            email="synthetic-ret-rct@example.test",
            documento="11223341011",
            password="test-password-not-real",
            first_name="RCT",
            last_name="User",
            is_staff=False,
            is_superuser=False,
        )
        role = _make_role("R-CT")
        assign_role_to_user(user, role)
        record = _make_record(11)
        response = self._patch(user, record.id, True)
        assert response.status_code == 403

    def test_r_aspirante_403(self, db):
        """R-ASPIRANTE → 403."""
        user = User.objects.create_user(
            email="synthetic-ret-asp@example.test",
            documento="11223341012",
            password="test-password-not-real",
            first_name="Aspirante",
            last_name="User",
            is_staff=False,
            is_superuser=False,
        )
        role = _make_role("R-ASPIRANTE")
        assign_role_to_user(user, role)
        record = _make_record(12)
        response = self._patch(user, record.id, True)
        assert response.status_code == 403

    def test_anonimo_401(self, db):
        """Unauthenticated → 401."""
        record = _make_record(20)
        response = APIClient().patch(self._url(record.id), {"retorno_archipelago": True})
        assert response.status_code == 401

    def test_retorno_archipelago_string_400(self, db):
        """Non-boolean value → 400."""
        user = _make_user(21, roles=["R-COORD"])
        record = _make_record(21)
        response = self._patch(user, record.id, "yes")  # string, not bool
        assert response.status_code == 400

    def test_retorno_archipelago_number_400(self, db):
        """Number instead of boolean → 400."""
        user = _make_user(22, roles=["R-COORD"])
        record = _make_record(22)
        response = self._patch(user, record.id, 1)  # int, not bool
        assert response.status_code == 400

    def test_retorno_archipelago_null_400(self, db):
        """null instead of boolean → 400."""
        user = _make_user(23, roles=["R-COORD"])
        record = _make_record(23)
        response = self._patch(user, record.id, None)
        assert response.status_code == 400

    def test_record_inexistente_404(self, db):
        """PATCH to non-existent record → 404."""
        user = _make_user(30, roles=["R-COORD"])
        import uuid

        fake_pk = uuid.uuid4()
        response = self._patch(user, fake_pk, True)
        assert response.status_code == 404

    def test_valor_mixed_bool_json_true(self, db):
        """JSON true (boolean) accepted; JSON 'true' (string) rejected."""
        user = _make_user(31, roles=["R-COORD"])
        record = _make_record(31)
        # DRF with format="json" sends booleans; string "true" would be from raw JSON text
        client = APIClient()
        client.force_authenticate(user=user)
        # Send as raw JSON string "true" instead of proper boolean
        response = client.patch(
            self._url(record.id),
            '{"retorno_archipelago": "true"}',
            content_type="application/json",
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# DB + Audit tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAnotarRetornoDB:
    """Test that the annotation persists and audit events are created."""

    def _do_patch(self, user, record, value):
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(user=user)
        return client.patch(
            f"/api/academic-tracking/records/{record.id}/anotar_retorno/",
            {"retorno_archipelago": value},
            format="json",
        )

    def test_anotacion_actualiza_db(self, db):
        """PATCH success → AcademicRecord.retorno_archipelago updated in DB."""
        user = _make_user(40, roles=["R-COORD"])
        record = _make_record(40)
        assert record.retorno_archipelago is None

        self._do_patch(user, record, True)

        record.refresh_from_db()
        assert record.retorno_archipelago is True

    def test_anotacion_genera_audit_event(self, db):
        """PATCH success → AuditEvent row created with action=academic_retorno_annotate."""
        user = _make_user(41, roles=["R-COORD"])
        record = _make_record(41)

        self._do_patch(user, record, True)

        # Query audit log
        events = AuditEvent.objects.filter(
            action="academic_retorno_annotate",
            entity="academicrecord",
        )
        assert events.count() == 1
        event = events.first()
        assert event.module == "academic_tracking"
        # Changes must contain the annotation value
        assert event.changes["after"]["retorno_archipelago"] is True
        assert event.actor == user

    def test_audit_fail_rollback(self, db):
        """log_audit_event raising → annotation rolled back (fail-closed)."""
        user = _make_user(50, roles=["R-COORD"])
        record = _make_record(50)

        with patch(
            "apps.academic_tracking.views.log_audit_event",
            side_effect=RuntimeError("audit broken"),
        ):
            response = self._do_patch(user, record, True)

        assert response.status_code == 500

        # Record should NOT be updated
        record.refresh_from_db()
        assert record.retorno_archipelago is None, (
            "Annotation must be rolled back when audit fails (fail-closed)"
        )

    def test_audit_fail_no_partial_update(self, db):
        """After failed audit, no partial state is visible."""
        user = _make_user(51, roles=["R-COORD"])
        record = _make_record(51)

        with patch(
            "apps.academic_tracking.views.log_audit_event",
            side_effect=RuntimeError("audit broken"),
        ):
            self._do_patch(user, record, False)

        record.refresh_from_db()
        assert record.retorno_archipelago is None
