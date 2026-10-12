"""Tests for Solicitud model — ies_nombre normalization in save()."""

import pytest

from apps.applications.models import Solicitud
from apps.convocatories.models import Convocatory
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestSolicitudIesNombreNormalization:
    """Test that Solicitud.save() normalizes ies_nombre with strip + space collapse."""

    @pytest.fixture
    def user(self, db):
        return User.objects.create_user(
            email="test_ies@example.com",
            documento="99988877",
            first_name="IESTest",
            last_name="User",
            password="testpass123",
        )

    @pytest.fixture
    def convocatoria(self, db):
        return Convocatory.objects.create(
            nombre="Convocatoria IES Test",
            estado=Convocatory.Estado.EN_INSCRIPCION,
        )

    def test_ies_nombre_normalizes_leading_trailing_spaces(self, user, convocatoria):
        """strip() removes leading and trailing whitespace."""
        solicitud = Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.BORRADOR,
            datos_academicos={},
        )
        solicitud.ies_nombre = "  Universidad Nacional  "
        solicitud.save()
        solicitud.refresh_from_db()
        assert solicitud.ies_nombre == "Universidad Nacional"

    def test_ies_nombre_normalizes_multiple_spaces(self, user, convocatoria):
        """re.sub(r' {2,}', ' ', ...) collapses multiple spaces."""
        solicitud = Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.BORRADOR,
            datos_academicos={},
        )
        solicitud.ies_nombre = "Universidad   Nacional  de  Colombia"
        solicitud.save()
        solicitud.refresh_from_db()
        assert solicitud.ies_nombre == "Universidad Nacional de Colombia"

    def test_ies_nombre_normalizes_both_strip_and_collapse(self, user, convocatoria):
        """Combined: leading/trailing spaces + internal multiple spaces."""
        solicitud = Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.BORRADOR,
            datos_academicos={},
        )
        solicitud.ies_nombre = "  Universidad  del   Valle  "
        solicitud.save()
        solicitud.refresh_from_db()
        assert solicitud.ies_nombre == "Universidad del Valle"

    def test_ies_nombre_preserves_single_spaces(self, user, convocatoria):
        """Single spaces between words are preserved."""
        solicitud = Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.BORRADOR,
            datos_academicos={},
        )
        solicitud.ies_nombre = "Universidad Nacional de Colombia"
        solicitud.save()
        solicitud.refresh_from_db()
        assert solicitud.ies_nombre == "Universidad Nacional de Colombia"

    def test_ies_nombre_preserves_case(self, user, convocatoria):
        """Normalization does NOT lowercase — case is preserved for display."""
        solicitud = Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.BORRADOR,
            datos_academicos={},
        )
        solicitud.ies_nombre = "UNIVERSIDAD  NACIONAL"
        solicitud.save()
        solicitud.refresh_from_db()
        assert solicitud.ies_nombre == "UNIVERSIDAD NACIONAL"
        # Ensure it's NOT lowercased
        assert solicitud.ies_nombre != "universidad nacional"

    def test_ies_nombre_null_remains_null(self, user, convocatoria):
        """Setting ies_nombre to None stays None after save."""
        solicitud = Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.BORRADOR,
            datos_academicos={},
        )
        solicitud.ies_nombre = None
        solicitud.save()
        solicitud.refresh_from_db()
        assert solicitud.ies_nombre is None

    def test_ies_nombre_empty_string_remains_empty(self, user, convocatoria):
        """Empty string stays empty (no normalization to null)."""
        solicitud = Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.BORRADOR,
            datos_academicos={},
        )
        solicitud.ies_nombre = ""
        solicitud.save()
        solicitud.refresh_from_db()
        assert solicitud.ies_nombre == ""
