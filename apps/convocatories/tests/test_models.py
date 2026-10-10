"""Tests for convocatories models."""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from apps.convocatories.models import (
    ConfiguracionConvocatoria,
    ConvocatoriaVersion,
    Convocatory,
    Cupo,
    Hito,
)


@pytest.mark.django_db
class TestConvocatory:
    """Test Convocatory model."""

    def test_convocatory_str_representation(self):
        """Test string representation of Convocatory."""
        # RED: This test references a field that doesn't exist yet
        convocatory = Convocatory.objects.create(
            codigo="TEST-2026-1",
            nombre="Convocatoria Test 2026-1",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
        )
        # Should use codigo in string representation
        assert str(convocatory) == "TEST-2026-1"

    def test_convocatory_codigo_unique(self):
        """Test codigo field must be unique."""
        # RED: This test expects unique constraint
        Convocatory.objects.create(
            codigo="DUPLICATE",
            nombre="Convocatoria 1",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
        )

        # Creating second with same codigo should raise IntegrityError
        with pytest.raises(IntegrityError):
            Convocatory.objects.create(
                codigo="DUPLICATE",
                nombre="Convocatoria 2",
                tipo=Convocatory.Tipo.PUBLICA,
                periodo="2026-2",
            )

    def test_convocatory_estado_choices(self):
        """Test estado field has correct choices."""
        # RED: This test expects Estado enum
        convocatory = Convocatory.objects.create(
            codigo="TEST-ESTADO",
            nombre="Convocatoria Test Estado",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
            estado=Convocatory.Estado.BORRADOR,
        )
        assert convocatory.estado == Convocatory.Estado.BORRADOR

    def test_convocatory_activas_manager(self):
        """Test activas manager filters ejecutable estados."""
        # RED: This test expects activas manager
        convocatory1 = Convocatory.objects.create(
            codigo="ACTIVE-1",
            nombre="Active Convocatoria",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
            estado=Convocatory.Estado.PUBLICADA,
        )
        convocatory2 = Convocatory.objects.create(
            codigo="DRAFT-1",
            nombre="Draft Convocatoria",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
            estado=Convocatory.Estado.BORRADOR,
        )

        # Only PUBLICADA should be in activas
        activas = Convocatory.activas.all()
        assert convocatory1 in activas
        assert convocatory2 not in activas


@pytest.mark.django_db
class TestConfiguracionConvocatoria:
    """Test ConfiguracionConvocatoria model."""

    def test_configuracion_convocatoria_one_to_one(self):
        """Test 1:1 relationship with Convocatory."""
        # RED: This test expects ConfiguracionConvocatoria model
        convocatory = Convocatory.objects.create(
            codigo="TEST-CONFIG",
            nombre="Convocatoria Config Test",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
        )

        config = ConfiguracionConvocatoria.objects.create(
            convocatoria=convocatory,
            schema_version="1.0.0",
            payload={"requisitos": []},
        )

        assert config.convocatoria == convocatory
        assert convocatory.config == config

    def test_configuracion_payload_default(self):
        """Test payload field has empty dict default."""
        # RED: This test expects payload with default
        convocatory = Convocatory.objects.create(
            codigo="TEST-DEFAULT",
            nombre="Convocatoria Default Test",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
        )

        config = ConfiguracionConvocatoria.objects.create(
            convocatoria=convocatory,
            schema_version="1.0.0",
            # No payload specified, should use default
        )

        assert config.payload == {}

    def test_configuracion_schema_version_required(self):
        """Test schema_version field is required."""
        # RED: This test expects schema_version field
        convocatory = Convocatory.objects.create(
            codigo="TEST-SCHEMA",
            nombre="Convocatoria Schema Test",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
        )

        # schema_version has default, so this should succeed
        config = ConfiguracionConvocatoria.objects.create(
            convocatoria=convocatory,
            payload={"requisitos": []},
        )
        assert config.schema_version == "1.0.0"


@pytest.mark.django_db
class TestHito:
    """Test Hito model."""

    def test_hito_foreign_key_to_config(self):
        """Test Hito FK to ConfiguracionConvocatoria."""
        # RED: This test expects Hito model
        convocatory = Convocatory.objects.create(
            codigo="TEST-HITO",
            nombre="Convocatoria Hito Test",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
        )

        config = ConfiguracionConvocatoria.objects.create(
            convocatoria=convocatory,
            schema_version="1.0.0",
            payload={},
        )

        hito = Hito.objects.create(
            config=config,
            codigo="inscripcion",
            orden=1,
            fecha_inicio=timezone.now(),
            fecha_fin=timezone.now() + timezone.timedelta(days=30),
            responsable="aspirante",
        )

        assert hito.config == config
        assert hito in config.hitos.all()

    def test_hito_codigo_required(self):
        """Test hito codigo field is required."""
        # RED: This test expects codigo field
        convocatory = Convocatory.objects.create(
            codigo="TEST-HITO-REQ",
            nombre="Convocatoria Hito Req Test",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
        )

        config = ConfiguracionConvocatoria.objects.create(
            convocatoria=convocatory,
            schema_version="1.0.0",
            payload={},
        )

        # codigo is required, this should fail with ValidationError
        with pytest.raises(ValidationError):
            hito = Hito(
                config=config,
                orden=1,
                fecha_inicio=timezone.now(),
                fecha_fin=timezone.now() + timezone.timedelta(days=30),
                responsable="aspirante",
            )
            hito.full_clean()


@pytest.mark.django_db
class TestCupo:
    """Test Cupo model."""

    def test_cupo_foreign_key_to_config_and_catalogs(self):
        """Test Cupo FK to ConfiguracionConvocatoria and core catalogs."""
        # RED: This test expects Cupo model with FK to core catalogs
        # We'll need to import core models
        from apps.core.models import ModalidadApoyo, MunicipioIsla, NivelFormacion

        # Create test catalog entries
        municipio = MunicipioIsla.objects.create(
            codigo="SAN_ANDRES",
            nombre="San Andrés",
            activo=True,
        )
        modalidad = ModalidadApoyo.objects.create(
            codigo="CEC",
            nombre="Crédito Educativo Condicionado",
            activo=True,
        )
        nivel = NivelFormacion.objects.create(
            codigo="PREGRADO",
            nombre="Pregrado",
            activo=True,
        )

        convocatory = Convocatory.objects.create(
            codigo="TEST-CUPO",
            nombre="Convocatoria Cupo Test",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
        )

        config = ConfiguracionConvocatoria.objects.create(
            convocatoria=convocatory,
            schema_version="1.0.0",
            payload={},
        )

        cupo = Cupo.objects.create(
            config=config,
            municipio=municipio,
            modalidad=modalidad,
            nivel=nivel,
            cantidad=10,
            regla_especial="",
        )

        assert cupo.config == config
        assert cupo.municipio == municipio
        assert cupo.modalidad == modalidad
        assert cupo.nivel == nivel
        assert cupo in config.cupos.all()


@pytest.mark.django_db
class TestConvocatoriaVersion:
    """Test ConvocatoriaVersion model."""

    def test_convocatoria_version_append_only(self):
        """Test ConvocatoriaVersion is append-only snapshot."""
        # RED: This test expects ConvocatoriaVersion model
        convocatory = Convocatory.objects.create(
            codigo="TEST-VERSION",
            nombre="Convocatoria Version Test",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
        )

        version = ConvocatoriaVersion.objects.create(
            convocatoria=convocatory,
            version=1,
            schema_version="1.0.0",
            snapshot={"config": {}},
            created_by=None,  # In real scenario would be a user
            valida_hasta=None,
        )

        assert version.convocatoria == convocatory
        assert version.version == 1

    def test_convocatoria_version_unique_together(self):
        """Test unique constraint on (convocatoria, version)."""
        # RED: This test expects unique constraint
        convocatory = Convocatory.objects.create(
            codigo="TEST-UNIQUE",
            nombre="Convocatoria Unique Test",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
        )

        ConvocatoriaVersion.objects.create(
            convocatoria=convocatory,
            version=1,
            schema_version="1.0.0",
            snapshot={},
        )

        # Creating second with same convocatory and version should raise IntegrityError
        with pytest.raises(IntegrityError):
            ConvocatoriaVersion.objects.create(
                convocatoria=convocatory,
                version=1,  # Same version!
                schema_version="1.0.0",
                snapshot={},
            )
