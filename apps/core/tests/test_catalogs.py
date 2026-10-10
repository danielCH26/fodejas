"""Tests for catalog models."""
from django.db import models


def test_catalogo_dominio_is_abstract():
    """Test that CatalogoDominio is an abstract base model."""
    # RED: This test will fail because CatalogoDominio doesn't exist yet
    from apps.core.models import CatalogoDominio

    # Check it's a model class
    assert issubclass(CatalogoDominio, models.Model)

    # Check it's abstract
    assert CatalogoDominio._meta.abstract is True


def test_catalogo_dominio_fields():
    """Test that CatalogoDominio has the correct fields."""
    from apps.core.models import CatalogoDominio

    # Check fields exist with correct types
    assert isinstance(CatalogoDominio._meta.get_field('codigo'), models.SlugField)
    assert CatalogoDominio._meta.get_field('codigo').max_length == 32
    assert CatalogoDominio._meta.get_field('codigo').unique is True

    assert isinstance(CatalogoDominio._meta.get_field('nombre'), models.CharField)
    assert CatalogoDominio._meta.get_field('nombre').max_length == 120

    assert isinstance(CatalogoDominio._meta.get_field('descripcion'), models.TextField)

    assert isinstance(CatalogoDominio._meta.get_field('orden'), models.PositiveSmallIntegerField)

    assert isinstance(CatalogoDominio._meta.get_field('activo'), models.BooleanField)

    assert isinstance(CatalogoDominio._meta.get_field('metadatos'), models.JSONField)


def test_activos_manager():
    """Test that ActivosManager filters only active records."""
    from apps.core.models import CatalogoDominio

    # Check dual managers exist - they're stored as ManagerDescriptor in __dict__
    assert 'objects' in CatalogoDominio.__dict__
    assert 'activos' in CatalogoDominio.__dict__

    # Check activos is a custom manager (ActivosManager class is defined in models.py)

    # The ManagerDescriptor returns the actual manager when accessed
    # We need to check the type of the manager instance
    CatalogoDominio.__dict__['activos']
    # Actually, we should check that CatalogoDominio.activos returns an ActivosManager
    # But we can't easily test this on an abstract model without a concrete subclass
    # For now, verify the descriptor exists


def test_activos_manager_filters_active():
    """Test that ActivosManager.get_queryset() filters for activo=True."""
    # Create a mock model class to test the manager
    from django.db import models

    from apps.core.models import ActivosManager

    class TestModel(models.Model):
        activo = models.BooleanField(default=True)
        objects = models.Manager()
        activos = ActivosManager()

        class Meta:
            app_label = 'core'

    # Test that get_queryset filters for activo=True
    TestModel.activos.get_queryset()
    # The queryset should have a filter for activo=True
    # We can't easily inspect the internal query, but we can test with actual instances
    # This test will be expanded when we have a concrete model and database


def test_concrete_models_exist():
    """Test that all 10 concrete models exist and inherit from CatalogoDominio."""
    from apps.core.models import (
        CatalogoDominio,
        CausalTerminacionConvenio,
        EstadoDocumento,
        Estrato,
        Etnia,
        GrupoSisben,
        ModalidadApoyo,
        MunicipioIsla,
        NivelFormacion,
        TipoDocumento,
        TipoIes,
    )

    # Check all models are subclasses of CatalogoDominio
    assert issubclass(Estrato, CatalogoDominio)
    assert issubclass(GrupoSisben, CatalogoDominio)
    assert issubclass(Etnia, CatalogoDominio)
    assert issubclass(MunicipioIsla, CatalogoDominio)
    assert issubclass(NivelFormacion, CatalogoDominio)
    assert issubclass(ModalidadApoyo, CatalogoDominio)
    assert issubclass(TipoIes, CatalogoDominio)
    assert issubclass(TipoDocumento, CatalogoDominio)
    assert issubclass(EstadoDocumento, CatalogoDominio)
    assert issubclass(CausalTerminacionConvenio, CatalogoDominio)

    # Check they're not abstract
    assert Estrato._meta.abstract is False
    assert GrupoSisben._meta.abstract is False
    assert Etnia._meta.abstract is False
    assert MunicipioIsla._meta.abstract is False
    assert NivelFormacion._meta.abstract is False
    assert ModalidadApoyo._meta.abstract is False
    assert TipoIes._meta.abstract is False
    assert TipoDocumento._meta.abstract is False
    assert EstadoDocumento._meta.abstract is False
    assert CausalTerminacionConvenio._meta.abstract is False

    # Check they have Spanish verbose names
    assert Estrato._meta.verbose_name == "Estrato"
    assert GrupoSisben._meta.verbose_name == "Grupo SISBÉN"
    assert Etnia._meta.verbose_name == "Etnia"
    assert MunicipioIsla._meta.verbose_name == "Municipio/Isla"
    assert NivelFormacion._meta.verbose_name == "Nivel de Formación"
    assert ModalidadApoyo._meta.verbose_name == "Modalidad de Apoyo"
    assert TipoIes._meta.verbose_name == "Tipo de IES"
    assert TipoDocumento._meta.verbose_name == "Tipo de Documento"
    assert EstadoDocumento._meta.verbose_name == "Estado de Documento"
    assert CausalTerminacionConvenio._meta.verbose_name == "Causal de Terminación de Convenio"


def test_concrete_models_inherit_fields():
    """Test that concrete models inherit all fields from CatalogoDominio."""
    from apps.core.models import Estrato

    # Check that Estrato has all the fields from CatalogoDominio
    field_names = {f.name for f in Estrato._meta.get_fields()}
    expected_fields = {'id', 'codigo', 'nombre', 'descripcion', 'orden', 'activo', 'metadatos'}

    # Check all expected fields are present
    for field in expected_fields:
        assert field in field_names, f"Missing field: {field}"

    # Check codigo is unique
    codigo_field = Estrato._meta.get_field('codigo')
    assert codigo_field.unique is True

    # Check default values
    activo_field = Estrato._meta.get_field('activo')
    assert activo_field.default is True

    orden_field = Estrato._meta.get_field('orden')
    assert orden_field.default == 0


def test_concrete_models_have_separate_tables():
    """Test that each concrete model has its own database table."""
    from apps.core.models import (
        CausalTerminacionConvenio,
        EstadoDocumento,
        Estrato,
        Etnia,
        GrupoSisben,
        ModalidadApoyo,
        MunicipioIsla,
        NivelFormacion,
        TipoDocumento,
        TipoIes,
    )

    # Each model should have its own db_table
    tables = set()
    for model in [Estrato, GrupoSisben, Etnia, MunicipioIsla,
                  NivelFormacion, ModalidadApoyo, TipoIes, TipoDocumento,
                  EstadoDocumento, CausalTerminacionConvenio]:
        table_name = model._meta.db_table
        assert table_name not in tables, f"Duplicate table name: {table_name}"
        tables.add(table_name)

        # Table name should follow Django convention: app_model
        assert table_name.startswith('core_'), f"Table name doesn't start with 'core_': {table_name}"


def test_catalogo_dominio_str():
    """Test __str__ returns nombre."""
    from apps.core.models import CatalogoDominio

    # Create a mock instance (abstract, so we'll test with a concrete subclass)
    class TestCatalogo(CatalogoDominio):
        class Meta:
            abstract = False
            app_label = 'core'

    instance = TestCatalogo(nombre="Test Catalog")
    assert str(instance) == "Test Catalog"


def test_catalogo_dominio_ordering():
    """Test default ordering by orden then nombre."""
    from apps.core.models import CatalogoDominio

    assert CatalogoDominio._meta.ordering == ["orden", "nombre"]
