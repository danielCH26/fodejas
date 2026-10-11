"""API tests for the academic tracking ViewSets (CHG-401)."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.academic_tracking.models import AcademicAlert
from apps.academic_tracking.services import AcademicTrackingService
from apps.convocatories.models import Convocatory
from apps.legalization.models import LegalizationProcess

User = get_user_model()


def _make_user(n, staff=False):
    return User.objects.create_user(
        email=f"synthetic-acad-api-{n}@example.test",
        documento=f"4567891{n:04d}",
        password="test-password-not-real",
        first_name="Aspirante",
        last_name="Ejemplo",
        is_staff=staff,
        is_superuser=staff,
    )


def _make_record(n):
    beneficiary = _make_user(50 + n)
    conv = Convocatory.objects.create(
        nombre=f"Conv CHG-401 API {n}",
        estado=Convocatory.Estado.EN_INSCRIPCION,
    )
    process = LegalizationProcess.objects.create(
        beneficiary=beneficiary,
        convocatoria=conv,
        status=LegalizationProcess.Status.LEGALIZADO,
    )
    return AcademicTrackingService.create_academic_record(process)


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
def record(db):
    return _make_record(1)


@pytest.mark.django_db
class TestAcademicRecordAPI:
    def test_list_requires_staff(self, staff_client, plain_client, record):
        assert staff_client.get("/api/academic-tracking/records/").status_code == 200
        assert plain_client.get("/api/academic-tracking/records/").status_code == 403

    def test_anonymous_is_unauthorized(self, db):
        assert APIClient().get("/api/academic-tracking/records/").status_code == 401

    def test_retrieve_includes_nested_grades_and_alerts(self, staff_client, record):
        AcademicTrackingService.add_grade(
            record.id, 1, "Materia A", 3, 4.5
        )
        response = staff_client.get(f"/api/academic-tracking/records/{record.id}/")
        assert response.status_code == 200
        assert response.data["cumulative_average"] == "4.50"
        assert len(response.data["grades"]) == 1
        assert response.data["grades"][0]["course_name"] == "Materia A"

    def test_add_grade_action(self, staff_client, record):
        response = staff_client.post(
            f"/api/academic-tracking/records/{record.id}/add_grade/",
            {
                "semester": 1,
                "course_name": "Materia Sintética",
                "credits": 3,
                "grade": "4.2",
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == record.Status.ACTIVO

    def test_add_grade_requires_all_fields(self, staff_client, record):
        response = staff_client.post(
            f"/api/academic-tracking/records/{record.id}/add_grade/",
            {"semester": 1},
            format="json",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestAcademicAlertAPI:
    def test_resolve_action_requires_staff(self, staff_client, plain_client, record):
        alert = AcademicTrackingService.create_alert(
            record, AcademicAlert.AlertType.PROBACION, "Sintético"
        )
        assert (
            plain_client.post(f"/api/academic-tracking/alerts/{alert.id}/resolve/").status_code
            == 403
        )
        response = staff_client.post(
            f"/api/academic-tracking/alerts/{alert.id}/resolve/"
        )
        assert response.status_code == 200
        assert response.data["status"] == "RESUELTA"
