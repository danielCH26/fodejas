"""Tests for catalog admin interface."""

from django.contrib import admin

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


def test_admin_registration():
    """Test that all catalog models are registered in admin."""

    # Check each model is registered
    assert Estrato in admin.site._registry
    assert GrupoSisben in admin.site._registry
    assert Etnia in admin.site._registry
    assert MunicipioIsla in admin.site._registry
    assert NivelFormacion in admin.site._registry
    assert ModalidadApoyo in admin.site._registry
    assert TipoIes in admin.site._registry
    assert TipoDocumento in admin.site._registry
    assert EstadoDocumento in admin.site._registry
    assert CausalTerminacionConvenio in admin.site._registry


def test_admin_list_display():
    """Test that admin has correct list_display configuration."""
    from django.contrib.admin.sites import site

    # Get the admin class for Estrato
    estrato_admin = site._registry[Estrato]

    # Check list_display
    expected_list_display = ("codigo", "nombre", "activo", "orden")
    assert estrato_admin.list_display == expected_list_display


def test_admin_list_filter():
    """Test that admin has activo filter."""
    from django.contrib.admin.sites import site

    estrato_admin = site._registry[Estrato]

    # Check list_filter includes activo
    assert "activo" in estrato_admin.list_filter


def test_admin_search_fields():
    """Test that admin has search fields for codigo and nombre."""
    from django.contrib.admin.sites import site

    estrato_admin = site._registry[Estrato]

    # Check search_fields
    expected_search_fields = ("codigo", "nombre")
    assert estrato_admin.search_fields == expected_search_fields


def test_admin_ordering():
    """Test that admin uses correct ordering."""
    from django.contrib.admin.sites import site

    estrato_admin = site._registry[Estrato]

    # Check ordering
    expected_ordering = ("orden", "nombre")
    assert estrato_admin.ordering == expected_ordering
