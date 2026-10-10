"""Tests for claims app (CHG-205, CHG-206)."""
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.claims.domain.transitions import (
    can_transition_to,
    get_transition_label,
    get_valid_apelacion_transitions,
    get_valid_transitions,
    is_valid_apelacion_transition,
    is_valid_transition,
)
from apps.claims.models import Apelacion, ApelacionHistorial, Reclamacion, ReclamacionHistorial

User = get_user_model()


def crear_reclamacion(solicitud, tipo, descripcion, evidencia=None, actor=None):
    """Wrapper for testing - imports from services."""
    from apps.claims.services import crear_reclamacion as _crear
    return _crear(solicitud, tipo, descripcion, evidencia, actor)


def cambiar_estado(reclamacion, nuevo_estado, observacion="", actor=None):
    """Wrapper for testing - imports from services."""
    from apps.claims.services import cambiar_estado as _cambiar
    return _cambiar(reclamacion, nuevo_estado, observacion, actor)


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        email="aspirante@test.co",
        documento="12345678",
        password="test123456",
        first_name="Test",
        last_name="Aspirante",
    )


@pytest.fixture
def junta_user(db):
    """Create junta user."""
    user = User.objects.create_user(
        email="junta@test.co",
        documento="87654321",
        password="test123456",
        first_name="Secretario",
        last_name="Junta",
        is_superuser=True,
    )
    return user


@pytest.fixture
def mock_solicitud(db, user):
    """Create mock solicitud."""
    solicitud = Mock()
    solicitud.pk = 1
    solicitud.uuid = "12345678-1234-1234-1234-123456789012"
    solicitud.aspirante = user
    solicitud.radicado = "FODEJAS-2025-0001"
    return solicitud


class TestReclamacionModel:
    """Tests for Reclamacion model."""

    def test_estado_choices(self):
        """Test estado choices are correct."""
        assert Reclamacion.Estado.PRESENTADA == "presentada"
        assert Reclamacion.Estado.EN_REVISION == "en_revision"
        assert Reclamacion.Estado.RESUELTA == "resuelta"
        assert Reclamacion.Estado.RECHAZADA == "rechazada"

    def test_tipo_choices(self):
        """Test tipo choices are correct."""
        assert Reclamacion.TipoReclamacion.PUNTAJE == "puntaje"
        assert Reclamacion.TipoReclamacion.REQUISITO == "requisito"
        assert Reclamacion.TipoReclamacion.OTRO == "otro"

    def test_default_estado(self):
        """Test default estado is PRESENTADA."""
        assert Reclamacion.Estado.PRESENTADA == Reclamacion._meta.get_field("estado").default


class TestReclamacionHistorial:
    """Tests for ReclamacionHistorial model."""

    def test_historial_fields(self):
        """Test required fields exist."""
        fields = [f.name for f in ReclamacionHistorial._meta.get_fields()]
        assert "reclamacion" in fields
        assert "estado_anterior" in fields
        assert "estado_nuevo" in fields
        assert "observacion" in fields
        assert "actor" in fields
        assert "created_at" in fields


class TestTransitions:
    """Tests for state transitions."""

    def test_valid_transition_presentada_to_en_revision(self):
        """Test valid transition from PRESENTADA to EN_REVISION."""
        assert is_valid_transition(
            Reclamacion.Estado.PRESENTADA,
            Reclamacion.Estado.EN_REVISION
        ) is True

    def test_valid_transition_en_revision_to_resuelta(self):
        """Test valid transition from EN_REVISION to RESUELTA."""
        assert is_valid_transition(
            Reclamacion.Estado.EN_REVISION,
            Reclamacion.Estado.RESUELTA
        ) is True

    def test_valid_transition_en_revision_to_rechazada(self):
        """Test valid transition from EN_REVISION to RECHAZADA."""
        assert is_valid_transition(
            Reclamacion.Estado.EN_REVISION,
            Reclamacion.Estado.RECHAZADA
        ) is True

    def test_invalid_transition_resuelta_to_presentada(self):
        """Test invalid transition from RESUELTA to PRESENTADA."""
        assert is_valid_transition(
            Reclamacion.Estado.RESUELTA,
            Reclamacion.Estado.PRESENTADA
        ) is False

    def test_invalid_transition_resuelta_to_anything(self):
        """Test RESUELTA is terminal state."""
        assert is_valid_transition(
            Reclamacion.Estado.RESUELTA,
            Reclamacion.Estado.EN_REVISION
        ) is False

    def test_invalid_transition_rechazada_to_anything(self):
        """Test RECHAZADA is terminal state."""
        assert is_valid_transition(
            Reclamacion.Estado.RECHAZADA,
            Reclamacion.Estado.PRESENTADA
        ) is False

    def test_get_valid_transitions_from_presentada(self):
        """Test get_valid_transitions from PRESENTADA."""
        valid = get_valid_transitions(Reclamacion.Estado.PRESENTADA)
        assert Reclamacion.Estado.EN_REVISION in valid
        assert Reclamacion.Estado.RECHAZADA in valid

    def test_get_valid_transitions_from_resuelta(self):
        """Test RESUELTA has no valid transitions."""
        valid = get_valid_transitions(Reclamacion.Estado.RESUELTA)
        assert valid == []

    def test_can_transition_to(self):
        """Test can_transition_to helper."""
        assert can_transition_to(
            Reclamacion.Estado.PRESENTADA,
            Reclamacion.Estado.EN_REVISION,
            Reclamacion.Estado.RESUELTA
        ) is True

        assert can_transition_to(
            Reclamacion.Estado.RESUELTA,
            Reclamacion.Estado.PRESENTADA
        ) is False

    def test_get_transition_label(self):
        """Test transition label generation."""
        label = get_transition_label(
            Reclamacion.Estado.PRESENTADA,
            Reclamacion.Estado.EN_REVISION
        )
        assert label == "Iniciar revisión"

        label = get_transition_label(
            Reclamacion.Estado.EN_REVISION,
            Reclamacion.Estado.RESUELTA
        )
        assert label == "Aceptar reclamación"


class TestCrearReclamacion:
    """Tests for crear_reclamacion service."""

    def test_crear_reclamacion_success(self, db, user, mock_solicitud):
        """Test successful claim creation."""
        with patch("apps.claims.models.Reclamacion.objects.create") as mock_create:
            mock_create.return_value = Mock(
                id=1,
                uuid="test-uuid",
                estado=Reclamacion.Estado.PRESENTADA,
            )
            with patch("apps.claims.models.ReclamacionHistorial.objects.create") as mock_historial:
                crear_reclamacion(
                    solicitud=mock_solicitud,
                    tipo=Reclamacion.TipoReclamacion.PUNTAJE,
                    descripcion="Puntaje incorrecto",
                    actor=user,
                )
                mock_create.assert_called_once()
                mock_historial.assert_called_once()

    def test_crear_reclamacion_ownership_check(self, db, user, mock_solicitud):
        """Test ownership validation."""
        other_user = Mock()
        other_user.id = 999

        with pytest.raises(PermissionError):
            crear_reclamacion(
                solicitud=mock_solicitud,
                tipo=Reclamacion.TipoReclamacion.PUNTAJE,
                descripcion="Test",
                actor=other_user,
            )


class TestCambiarEstado:
    """Tests for cambiar_estado service."""

    def test_cambiar_estado_valid_transition(self, db):
        """Test valid state change."""
        mock_reclamacion = Mock()
        mock_reclamacion.estado = Reclamacion.Estado.PRESENTADA
        mock_reclamacion.save = Mock()

        with patch("apps.claims.models.ReclamacionHistorial.objects.create"):
            cambiar_estado(
                mock_reclamacion,
                Reclamacion.Estado.EN_REVISION,
                observacion="Iniciando revisión",
            )
            mock_reclamacion.save.assert_called_once()

    def test_cambiar_estado_invalid_transition(self, db):
        """Test invalid state change raises error."""
        mock_reclamacion = Mock()
        mock_reclamacion.estado = Reclamacion.Estado.RESUELTA

        with pytest.raises(ValueError, match="Transición inválida"):
            cambiar_estado(
                mock_reclamacion,
                Reclamacion.Estado.PRESENTADA,
            )


class TestIntegration:
    """Integration tests for claims workflow."""

    def test_full_transition_path(self):
        """Test full workflow: PRESENTADA -> EN_REVISION -> RESUELTA."""
        # PRESENTADA -> EN_REVISION is valid
        assert is_valid_transition(
            Reclamacion.Estado.PRESENTADA,
            Reclamacion.Estado.EN_REVISION
        )

        # EN_REVISION -> RESUELTA is valid
        assert is_valid_transition(
            Reclamacion.Estado.EN_REVISION,
            Reclamacion.Estado.RESUELTA
        )

        # RESUELTA is terminal
        assert get_valid_transitions(Reclamacion.Estado.RESUELTA) == []

    def test_rejection_path(self):
        """Test rejection workflow."""
        # PRESENTADA -> RECHAZADA (vencimiento)
        assert is_valid_transition(
            Reclamacion.Estado.PRESENTADA,
            Reclamacion.Estado.RECHAZADA
        )

        # EN_REVISION -> RECHAZADA
        assert is_valid_transition(
            Reclamacion.Estado.EN_REVISION,
            Reclamacion.Estado.RECHAZADA
        )


# ============================================================================
# Apelacion Tests (CHG-206)
# ============================================================================

class TestApelacionModel:
    """Tests for Apelacion model."""

    def test_estado_choices(self):
        """Test estado choices are correct."""
        assert Apelacion.Estado.PRESENTADA == "presentada"
        assert Apelacion.Estado.EN_ANALISIS == "en_analisis"
        assert Apelacion.Estado.CONFIRMADA == "confirmada"
        assert Apelacion.Estado.REVOCADA == "revocada"

    def test_default_estado(self):
        """Test default estado is PRESENTADA."""
        assert Apelacion.Estado.PRESENTADA == Apelacion._meta.get_field("estado").default


class TestApelacionHistorial:
    """Tests for ApelacionHistorial model."""

    def test_historial_fields(self):
        """Test required fields exist."""
        fields = [f.name for f in ApelacionHistorial._meta.get_fields()]
        assert "apelacion" in fields
        assert "estado_anterior" in fields
        assert "estado_nuevo" in fields
        assert "observacion" in fields
        assert "actor" in fields
        assert "created_at" in fields


class TestApelacionTransitions:
    """Tests for apelacion state transitions."""

    def test_valid_transition_presentada_to_en_analisis(self):
        """Test valid transition from PRESENTADA to EN_ANALISIS."""
        assert is_valid_apelacion_transition(
            Apelacion.Estado.PRESENTADA,
            Apelacion.Estado.EN_ANALISIS
        )

    def test_valid_transition_en_analisis_to_confirmada(self):
        """Test valid transition from EN_ANALISIS to CONFIRMADA."""
        assert is_valid_apelacion_transition(
            Apelacion.Estado.EN_ANALISIS,
            Apelacion.Estado.CONFIRMADA
        )

    def test_valid_transition_en_analisis_to_revocada(self):
        """Test valid transition from EN_ANALISIS to REVOCADA."""
        assert is_valid_apelacion_transition(
            Apelacion.Estado.EN_ANALISIS,
            Apelacion.Estado.REVOCADA
        )

    def test_terminal_states(self):
        """Test CONFIRMADA and REVOCADA are terminal."""
        assert get_valid_apelacion_transitions(Apelacion.Estado.CONFIRMADA) == []
        assert get_valid_apelacion_transitions(Apelacion.Estado.REVOCADA) == []


class TestValidarApelacion:
    """Tests for validar_apelacion service."""

    def test_validar_reclamacion_no_terminal(self, db, user, mock_solicitud):
        """Test validation fails if claim is not in terminal state."""
        from apps.claims.services.apelaciones import validar_apelacion

        mock_reclamacion = Mock()
        mock_reclamacion.estado = Reclamacion.Estado.EN_REVISION
        mock_reclamacion.fecha_resolucion = None
        mock_reclamacion.solicitud.aspirante = user

        is_valid, error = validar_apelacion(mock_reclamacion, user)

        assert is_valid is False
        assert "resuelta o rechazada" in error

    def test_validar_plazo_vencido(self, db, user, mock_solicitud):
        """Test validation fails if 30-day window is expired."""
        from apps.claims.services.apelaciones import validar_apelacion

        mock_reclamacion = Mock()
        mock_reclamacion.estado = Reclamacion.Estado.RESUELTA
        mock_reclamacion.fecha_resolucion = timezone.now() - timezone.timedelta(days=31)
        mock_reclamacion.solicitud.aspirante = user

        is_valid, error = validar_apelacion(mock_reclamacion, user)

        assert is_valid is False
        assert "30 días" in error

    def test_validar_no_titular(self, db, user, mock_solicitud):
        """Test validation fails if user is not the titular."""
        from apps.claims.services.apelaciones import validar_apelacion

        other_user = Mock()
        other_user.id = 999

        mock_reclamacion = Mock()
        mock_reclamacion.estado = Reclamacion.Estado.RESUELTA
        mock_reclamacion.fecha_resolucion = timezone.now()
        mock_reclamacion.solicitud.aspirante = other_user

        is_valid, error = validar_apelacion(mock_reclamacion, user)

        assert is_valid is False
        assert "aspirante" in error


class TestCrearApelacion:
    """Tests for crear_apelacion service."""

    def test_crear_apelacion_model_import(self):
        """Test that Apelacion model can be imported."""
        from apps.claims.models import Apelacion
        assert Apelacion is not None
        assert hasattr(Apelacion, 'Estado')


class TestTransitionPermissions:
    """Tests for transition permission checks."""

    def test_iniciar_analisis_requires_ofijur(self, db, user):
        """Test iniciar_analisis requires R-OFIJUR role."""
        from apps.claims.services.apelaciones import iniciar_analisis

        mock_apelacion = Mock()
        mock_apelacion.estado = Apelacion.Estado.PRESENTADA
        mock_apelacion.save = Mock()

        # Without OFIJUR role, should raise
        with pytest.raises(PermissionError):
            iniciar_analisis(mock_apelacion, user)

    def test_confirmar_requires_ofijur(self, db, user):
        """Test confirmar requires R-OFIJUR role."""
        from apps.claims.services.apelaciones import confirmar_apelacion

        mock_apelacion = Mock()
        mock_apelacion.estado = Apelacion.Estado.EN_ANALISIS
        mock_apelacion.save = Mock()

        # Without OFIJUR role, should raise
        with pytest.raises(PermissionError):
            confirmar_apelacion(mock_apelacion, "Test response", user)

    def test_confirmar_requires_respuesta(self, db, user):
        """Test confirmar requires respuesta."""
        from apps.claims.services.apelaciones import confirmar_apelacion

        mock_apelacion = Mock()
        mock_apelacion.estado = Apelacion.Estado.EN_ANALISIS
        mock_apelacion.save = Mock()

        # User with OFIJUR role (simulated via superuser)
        user.is_superuser = True

        # Without respuesta, should raise
        with pytest.raises(ValueError, match="respuesta"):
            confirmar_apelacion(mock_apelacion, "", user)


class TestApelacionIntegration:
    """Integration tests for apelacion workflow."""

    def test_full_appeal_workflow(self):
        """Test complete appeal workflow: PRESENTADA -> EN_ANALISIS -> CONFIRMADA."""
        # PRESENTADA -> EN_ANALISIS
        assert is_valid_apelacion_transition(
            Apelacion.Estado.PRESENTADA,
            Apelacion.Estado.EN_ANALISIS
        )

        # EN_ANALISIS -> CONFIRMADA
        assert is_valid_apelacion_transition(
            Apelacion.Estado.EN_ANALISIS,
            Apelacion.Estado.CONFIRMADA
        )

        # CONFIRMADA is terminal
        assert get_valid_apelacion_transitions(Apelacion.Estado.CONFIRMADA) == []

    def test_rejection_workflow(self):
        """Test rejection workflow: PRESENTADA -> EN_ANALISIS -> REVOCADA."""
        # PRESENTADA -> EN_ANALISIS
        assert is_valid_apelacion_transition(
            Apelacion.Estado.PRESENTADA,
            Apelacion.Estado.EN_ANALISIS
        )

        # EN_ANALISIS -> REVOCADA
        assert is_valid_apelacion_transition(
            Apelacion.Estado.EN_ANALISIS,
            Apelacion.Estado.REVOCADA
        )

        # REVOCADA is terminal
        assert get_valid_apelacion_transitions(Apelacion.Estado.REVOCADA) == []
