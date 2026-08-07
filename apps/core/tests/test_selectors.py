"""Tests for catalog selectors."""
import pytest
from django.db import transaction

from apps.core.models import (
    Estrato, GrupoSisben, Etnia, MunicipioIsla, NivelFormacion,
    ModalidadApoyo, TipoIes, TipoDocumento, EstadoDocumento,
    CausalTerminacionConvenio
)


@pytest.mark.django_db
def test_get_estratos_activos():
    """Test get_estratos_activos selector returns active records ordered."""
    from apps.core.selectors import get_estratos_activos
    
    # Create test data
    with transaction.atomic():
        Estrato.objects.create(codigo='1', nombre='Estrato 1', activo=True, orden=10)
        Estrato.objects.create(codigo='2', nombre='Estrato 2', activo=False, orden=5)  # inactive
        Estrato.objects.create(codigo='3', nombre='Estrato 3', activo=True, orden=15)
        Estrato.objects.create(codigo='4', nombre='Estrato 4', activo=True, orden=5)  # same order as 2
    
    # Call selector
    results = get_estratos_activos()
    
    # Should return only active records
    assert results.count() == 3
    
    # Should be ordered by orden, then nombre
    expected_order = ['4', '1', '3']  # orden: 5, 10, 15
    actual_order = [e.codigo for e in results]
    assert actual_order == expected_order
    
    # Check all returned records are active
    for estrato in results:
        assert estrato.activo is True


@pytest.mark.django_db
def test_get_grupos_sisben_activos():
    """Test get_grupos_sisben_activos selector."""
    from apps.core.selectors import get_grupos_sisben_activos
    
    with transaction.atomic():
        GrupoSisben.objects.create(codigo='A', nombre='Grupo A', activo=True, orden=1)
        GrupoSisben.objects.create(codigo='B', nombre='Grupo B', activo=False, orden=2)
    
    results = get_grupos_sisben_activos()
    assert results.count() == 1
    assert results.first().codigo == 'A'


@pytest.mark.django_db
def test_get_etnias_activas():
    """Test get_etnias_activas selector."""
    from apps.core.selectors import get_etnias_activas
    
    with transaction.atomic():
        Etnia.objects.create(codigo='raizal', nombre='Raizal', activo=True, orden=1)
        Etnia.objects.create(codigo='afro', nombre='Afrodescendiente', activo=True, orden=2)
    
    results = get_etnias_activas()
    assert results.count() == 2


@pytest.mark.django_db
def test_get_municipios_islas_activos():
    """Test get_municipios_islas_activos selector."""
    from apps.core.selectors import get_municipios_islas_activos
    
    with transaction.atomic():
        MunicipioIsla.objects.create(codigo='san-andres', nombre='San Andrés', activo=True, orden=1)
        MunicipioIsla.objects.create(codigo='providencia', nombre='Providencia', activo=True, orden=2)
    
    results = get_municipios_islas_activos()
    assert results.count() == 2


@pytest.mark.django_db
def test_get_niveles_formacion_activos():
    """Test get_niveles_formacion_activos selector."""
    from apps.core.selectors import get_niveles_formacion_activos
    
    with transaction.atomic():
        NivelFormacion.objects.create(codigo='tecnico', nombre='Técnico profesional', activo=True, orden=1)
        NivelFormacion.objects.create(codigo='tecnologico', nombre='Tecnológico', activo=True, orden=2)
    
    results = get_niveles_formacion_activos()
    assert results.count() == 2


@pytest.mark.django_db
def test_get_modalidades_apoyo_activas():
    """Test get_modalidades_apoyo_activas selector."""
    from apps.core.selectors import get_modalidades_apoyo_activas
    
    with transaction.atomic():
        ModalidadApoyo.objects.create(codigo='credito', nombre='Crédito educativo condonable', activo=True, orden=1)
        ModalidadApoyo.objects.create(codigo='beca', nombre='Beca', activo=True, orden=2)
    
    results = get_modalidades_apoyo_activas()
    assert results.count() == 2


@pytest.mark.django_db
def test_get_tipos_ies_activos():
    """Test get_tipos_ies_activos selector."""
    from apps.core.selectors import get_tipos_ies_activos
    
    with transaction.atomic():
        TipoIes.objects.create(codigo='publica-oficial', nombre='Pública oficial', activo=True, orden=1)
        TipoIes.objects.create(codigo='privada', nombre='Privada', activo=True, orden=2)
    
    results = get_tipos_ies_activos()
    assert results.count() == 2


@pytest.mark.django_db
def test_get_tipos_documento_activos():
    """Test get_tipos_documento_activos selector."""
    from apps.core.selectors import get_tipos_documento_activos
    
    with transaction.atomic():
        TipoDocumento.objects.create(codigo='cc', nombre='Cédula de ciudadanía', activo=True, orden=1)
        TipoDocumento.objects.create(codigo='ce', nombre='Cédula de extranjería', activo=True, orden=2)
    
    results = get_tipos_documento_activos()
    assert results.count() == 2


@pytest.mark.django_db
def test_get_estados_documento_activos():
    """Test get_estados_documento_activos selector."""
    from apps.core.selectors import get_estados_documento_activos
    
    with transaction.atomic():
        EstadoDocumento.objects.create(codigo='pendiente', nombre='Pendiente', activo=True, orden=1)
        EstadoDocumento.objects.create(codigo='aprobado', nombre='Aprobado', activo=True, orden=2)
    
    results = get_estados_documento_activos()
    assert results.count() == 2


@pytest.mark.django_db
def test_get_causales_terminacion_convenio_activas():
    """Test get_causales_terminacion_convenio_activas selector."""
    # Import here to avoid pytest collection issues
    from apps.core.selectors import get_causales_terminacion_convenio_activos as selector_fn
    
    with transaction.atomic():
        CausalTerminacionConvenio.objects.create(
            codigo='abandono', nombre='Abandono', activo=True, orden=1)
        CausalTerminacionConvenio.objects.create(
            codigo='bajo-rendimiento', nombre='Bajo rendimiento', activo=True, orden=2)
    
    results = selector_fn()
    assert results.count() == 2