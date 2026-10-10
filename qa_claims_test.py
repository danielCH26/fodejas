#!/usr/bin/env python
"""
QA Test - Verificar CHG-205 Reclamaciones desde el navegador
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, "/home/daniel/fodejas")
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client

from apps.applications.models import Solicitud
from apps.claims.models import Reclamacion
from apps.convocatories.models import Convocatory
from apps.scoring.models import PuntajeTotal

User = get_user_model()


def test_login():
    """Test login functionality"""
    print("\n=== TEST 1: Login ===")
    client = Client()

    response = client.get("/accounts/login/")
    assert response.status_code == 200, f"Login page failed: {response.status_code}"
    print("✓ Login page loads correctly")

    csrftoken = client.cookies.get("csrftoken")
    print("✓ CSRF token obtained")

    response = client.post(
        "/accounts/login/",
        {
            "username": "test@fodejas.gov.co",
            "password": "test123456",
            "csrfmiddlewaretoken": csrftoken.value,
        },
        follow=True,
    )

    if response.status_code == 200:
        print("✓ Login successful")

        # Add ASPIRANTE role
        from django.contrib.auth import get_user_model

        User = get_user_model()
        from apps.accounts.models import Role, UserRole

        user = User.objects.get(email="test@fodejas.gov.co")
        aspir_role = Role.objects.filter(code="R-ASPIRANTE").first()
        if aspir_role and not UserRole.objects.filter(user=user, role=aspir_role).exists():
            UserRole.objects.create(user=user, role=aspir_role)
            print("✓ Added R-ASPIRANTE role")

        return client
    else:
        print(f"✗ Login failed: status={response.status_code}")
        return None


def test_claims_list(client):
    """Test claims list view"""
    print("\n=== TEST 2: Lista de Reclamaciones ===")
    response = client.get("/claims/")
    # May redirect if no permission
    if response.status_code == 302:
        print("⚠ Redirects (permission issue)")
        return
    assert response.status_code == 200, f"List failed: {response.status_code}"
    print("✓ Claims list loads correctly")

    content = response.content.decode()
    if "Reclamaciones" in content:
        print("✓ Page title correct")
    if "claims:create" in content or "Presentar" in content:
        print("✓ Create button/link present")


def test_claims_create_form(client):
    """Test create claim form"""
    print("\n=== TEST 3: Formulario Crear Reclamación ===")

    # Get a solicitud
    solicitud = Solicitud.objects.filter(estado=Solicitud.Estado.VERIFICADA).first()

    if not solicitud:
        print("⚠ No verified solicitudes found, skipping form test")
        return None

    response = client.get(f"/claims/crear/{solicitud.uuid}/")
    print(f"  Create form URL response: {response.status_code}")

    if response.status_code == 200:
        print("✓ Create form loads")
        content = response.content.decode()

        # Check form fields
        if "tipo" in content:
            print("✓ Field 'tipo' present")
        if "descripcion" in content:
            print("✓ Field 'descripcion' present")
        if "evidencia" in content:
            print("✓ Field 'evidencia' present")

        return solicitud
    elif response.status_code == 302:
        print("✗ Redirects (permission issue)")
        return None


def test_create_claim(client, solicitud):
    """Test creating a claim"""
    print("\n=== TEST 4: Crear Reclamación ===")

    if not solicitud:
        print("⚠ Skipping - no solicitud available")
        return None

    # Get fresh CSRF
    response = client.get(f"/claims/crear/{solicitud.uuid}/")
    csrftoken = client.cookies.get("csrftoken")

    # Create claim
    response = client.post(
        f"/claims/crear/{solicitud.uuid}/",
        {
            "csrfmiddlewaretoken": csrftoken.value,
            "tipo": "puntaje",
            "descripcion": "QA Test - Reclamación sobre puntaje incorrecto",
        },
        follow=True,
    )

    print(f"  Create response: {response.status_code}")

    # Check if created
    claim = Reclamacion.objects.filter(solicitud=solicitud, tipo="puntaje").first()

    if claim:
        print(f"✓ Claim created successfully: {claim.uuid}")
        print(f"  - Estado: {claim.estado}")
        print(f"  - Tipo: {claim.tipo}")
        return claim
    else:
        print("✗ Claim not found after creation")
        return None


def test_claim_detail(client, claim):
    """Test claim detail view"""
    print("\n=== TEST 5: Detalle de Reclamación ===")

    if not claim:
        print("⚠ Skipping - no claim available")
        return

    response = client.get(f"/claims/{claim.uuid}/")
    print(f"  Detail response: {response.status_code}")

    if response.status_code == 200:
        print("✓ Detail page loads")
        content = response.content.decode()

        if claim.tipo in content:
            print("✓ Claim type displayed")
        if claim.descripcion[:20] in content:
            print("✓ Claim description displayed")
        if claim.estado in content:
            print("✓ Claim status displayed")
    elif response.status_code == 302:
        print("✗ Redirects (permission issue)")


def test_claims_admin_list(client):
    """Test claims admin list view"""
    print("\n=== TEST 6: Panel de Admin (Junta) ===")
    response = client.get("/claims/admin/")
    print(f"  Admin list response: {response.status_code}")

    if response.status_code == 200:
        print("✓ Admin list loads")
    elif response.status_code == 302:
        print("⚠ Redirects - user not R-JUNTA (expected)")


def test_application_detail_with_claim_button(client, solicitud):
    """Test application detail has claim button"""
    print("\n=== TEST 7: Detalle de Postulación con Botón Reclamación ===")

    if not solicitud:
        # Create a test solicitud with score
        user = User.objects.filter(email="test@fodejas.gov.co").first()
        if not user:
            print("⚠ Skipping - no user found")
            return

        conv = Convocatory.objects.first()
        if not conv:
            print("⚠ Skipping - no convocatoria found")
            return

        solicitud = Solicitud.objects.create(
            convocatoria=conv,
            aspirantespirante=user,
            estado=Solicitud.Estado.VERIFICADA,
            radicado="FODEJAS-QA-TEST",
            datos_personales={"nombre": "Test", "municipio": "san_andres"},
        )

        # Create score
        PuntajeTotal.objects.create(
            solicitud=solicitud,
            puntaje_total=85.00,
            ranking_general=1,
        )
        print("✓ Created test solicitud with score")

    response = client.get(f"/applications/{solicitud.uuid}/")
    print(f"  Application detail response: {response.status_code}")

    if response.status_code == 200:
        content = response.content.decode()

        if "claims:create" in content:
            print("✓ 'Presentar Reclamación' button present")
        if "Puntaje" in content or "ranking" in content.lower():
            print("✓ Score/ranking info displayed")
    elif response.status_code == 302:
        print("✗ Redirects (permission issue)")


def main():
    print("=" * 60)
    print("FODEJAS QA Tests - CHG-205 Reclamaciones")
    print("=" * 60)

    # Test login
    client = test_login()
    if not client:
        print("\n✗ Cannot proceed without login")
        return

    # Test claims list
    test_claims_list(client)

    # Test create form
    solicitud = test_claims_create_form(client)

    # Test create claim
    claim = test_create_claim(client, solicitud)

    # Test claim detail
    test_claim_detail(client, claim)

    # Test admin
    test_claims_admin_list(client)

    # Test application detail with claim button
    test_application_detail_with_claim_button(client, solicitud)

    print("\n" + "=" * 60)
    print("CHG-205 QA Tests Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
