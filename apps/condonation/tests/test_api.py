"""API tests for the condonation ViewSets (CHG-304)."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.condonation.models import Sanction, TerminationRequest
from apps.condonation.services import TerminationService
from apps.convocatories.models import Convocatory
from apps.legalization.models import LegalizationProcess

User = get_user_model()


def _make_user(n, staff=False):
    return User.objects.create_user(
        email=f"synthetic-cond-{n}-{n * 7}@example.test",
        documento=f"7654321{n:04d}",
        password="test-password-not-real",
        first_name="Aspirante",
        last_name="Ejemplo",
        is_staff=staff,
        is_superuser=staff,
    )


def _make_legalized_process(beneficiary):
    conv = Convocatory.objects.create(
        nombre=f"Conv CHG-304 API {beneficiary.id}",
        estado=Convocatory.Estado.EN_INSCRIPCION,
    )
    return LegalizationProcess.objects.create(
        beneficiary=beneficiary,
        convocatoria=conv,
        status=LegalizationProcess.Status.LEGALIZADO,
    )


@pytest.fixture
def staff_client(db):
    client = APIClient()
    client.force_authenticate(user=_make_user(1, staff=True))
    return client


@pytest.fixture
def plain_client(db):
    client = APIClient()
    client.force_authenticate(user=_make_user(2, staff=False))
    return client


@pytest.fixture
def anonymous_client():
    return APIClient()


@pytest.fixture
def legalized_process(db):
    return _make_legalized_process(_make_user(3))


@pytest.mark.django_db
class TestTerminationAPI:
    def test_list_requires_staff(self, staff_client, plain_client, legalized_process):
        requester = _make_user(7)
        TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.ABANDONO, requester
        )
        assert staff_client.get("/api/condonation/terminations/").status_code == 200
        assert plain_client.get("/api/condonation/terminations/").status_code == 403

    def test_anonymous_is_unauthorized(self, anonymous_client):
        assert anonymous_client.get("/api/condonation/terminations/").status_code == 401

    def test_create_through_custom_action(self, staff_client, legalized_process):
        response = staff_client.post(
            "/api/condonation/terminations/",
            {
                "legalization_process": str(legalized_process.id),
                "cause": TerminationRequest.Cause.ABANDONO,
                "description": "Solicitud sintética de terminación",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["status"] == TerminationRequest.Status.PENDIENTE

    def test_create_requires_process_and_cause(self, staff_client):
        response = staff_client.post("/api/condonation/terminations/", {}, format="json")
        assert response.status_code == 400

    def test_retrieve_uses_serializer(self, staff_client, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.ABANDONO, None
        )
        response = staff_client.get(f"/api/condonation/terminations/{termination.id}/")
        assert response.status_code == 200
        assert response.data["cause"] == TerminationRequest.Cause.ABANDONO

    def test_approve_action(self, staff_client, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.RETIRO_VOLUNTARIO, None
        )
        response = staff_client.post(f"/api/condonation/terminations/{termination.id}/approve/")
        assert response.status_code == 200
        assert response.data["status"] == TerminationRequest.Status.TERMINADO


@pytest.mark.django_db
class TestSanctionAPI:
    @pytest.fixture
    def pending_sanction(self, db):
        reviewer = _make_user(4, staff=True)
        process = _make_legalized_process(_make_user(5))
        termination = TerminationService.create_termination(
            process, TerminationRequest.Cause.INFORMACION_FALSA, reviewer
        )
        TerminationService.approve_termination(termination.id, reviewer)
        return Sanction.objects.get(termination=termination)

    def test_list_requires_staff(self, staff_client, plain_client, pending_sanction):
        assert staff_client.get("/api/condonation/sanctions/").status_code == 200
        assert plain_client.get("/api/condonation/sanctions/").status_code == 403

    def test_retrieve_exposes_amounts(self, staff_client, pending_sanction):
        pending_sanction.base_amount = 1000
        pending_sanction.ipc_adjustment = 50
        pending_sanction.total_amount = 1050
        pending_sanction.save()
        response = staff_client.get(f"/api/condonation/sanctions/{pending_sanction.id}/")
        assert response.status_code == 200
        assert response.data["total_amount"] == "1050.00"

    def test_beneficiary_can_submit_justification(self, db, pending_sanction):
        beneficiary = _make_user(6)
        client = APIClient()
        client.force_authenticate(user=beneficiary)
        response = client.post(
            f"/api/condonation/sanctions/{pending_sanction.id}/submit_justification/",
            {
                "justification": Sanction.Justification.ENFERMEDAD_GRAVE,
                "details": "Certificado sintético",
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == Sanction.Status.EN_REVISION

    def test_submit_justification_requires_authentication(self, anonymous_client, pending_sanction):
        response = anonymous_client.post(
            f"/api/condonation/sanctions/{pending_sanction.id}/submit_justification/",
            {"justification": Sanction.Justification.ACCIDENTE},
            format="json",
        )
        assert response.status_code == 401
