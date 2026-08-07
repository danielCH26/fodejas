#!/usr/bin/env python
"""
QA Test - Verificar formularios de Convocation desde el navegador
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/home/daniel/fodejas')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.convocatories.models import Convocatory

User = get_user_model()

def test_login():
    """Test login functionality"""
    print("\n=== TEST 1: Login ===")
    client = Client()
    
    # Get login page
    response = client.get('/accounts/login/')
    assert response.status_code == 200, f"Login page failed: {response.status_code}"
    print("✓ Login page loads correctly")
    
    # Get CSRF token
    csrftoken = client.cookies.get('csrftoken')
    print(f"✓ CSRF token obtained: {csrftoken.value[:20]}...")
    
    # Login
    response = client.post('/accounts/login/', {
        'username': 'test@fodejas.gov.co',
        'password': 'test123456',
        'csrfmiddlewaretoken': csrftoken.value
    }, follow=True)
    
    # Check if logged in
    if response.status_code == 200 and 'dashboard' in response.request.get('PATH_INFO', ''):
        print("✓ Login successful")
        
        # Add admin role to user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        from apps.accounts.models import Role, UserRole
        
        user = User.objects.get(email='test@fodejas.gov.co')
        admin_role = Role.objects.filter(code='R-ADMIN').first()
        if admin_role and not UserRole.objects.filter(user=user, role=admin_role).exists():
            UserRole.objects.create(user=user, role=admin_role)
            print("✓ Added R-ADMIN role to user")
        
        return client
    else:
        print(f"✗ Login failed: status={response.status_code}")
        return None


def test_convocatoria_list(client):
    """Test convocatoria list view"""
    print("\n=== TEST 2: Convocatoria List ===")
    response = client.get('/convocatorias/')
    # May redirect if no permission
    if response.status_code == 302:
        print("✓ Convocatoria list redirects (requires permission)")
        return
    assert response.status_code == 200, f"List failed: {response.status_code}"
    print("✓ Convocatoria list loads correctly")
    
    # Check if "Nueva Convocatoria" button exists
    if 'Nueva Convocatoria' in response.content.decode():
        print("✓ 'Nueva Convocatoria' button present")
    else:
        print("✗ 'Nueva Convocatoria' button not found")


def test_convocatoria_create_form(client):
    """Test create convocation form"""
    print("\n=== TEST 3: Create Convocatoria Form ===")
    response = client.get('/convocatorias/crear/')
    assert response.status_code == 200, f"Create form failed: {response.status_code}"
    print("✓ Create form loads correctly")
    
    # Check form fields
    content = response.content.decode()
    fields = ['nombre', 'codigo', 'tipo', 'periodo', 'cupo_total', 
              'monto_semestre_smlmv', 'duracion_maxima_semestres']
    
    for field in fields:
        if f'name="{field}"' in content:
            print(f"✓ Field '{field}' present")
        else:
            print(f"✗ Field '{field}' missing")


def test_create_convocatoria(client):
    """Test creating a convocation"""
    print("\n=== TEST 4: Create Convocatoria ===")
    
    # Get fresh CSRF
    response = client.get('/convocatorias/crear/')
    csrftoken = client.cookies.get('csrftoken')
    
    # Create convocation
    response = client.post('/convocatorias/crear/', {
        'csrfmiddlewaretoken': csrftoken.value,
        'nombre': 'Convocatoria Prueba QA',
        'codigo': 'QA-TEST-2026',
        'tipo': 'publica',
        'periodo': '2026-1',
        'cupo_total': '50',
        'monto_semestre_smlmv': '5',
        'duracion_maxima_semestres': '4',
        'fecha_apertura_inscripcion': '2026-07-01',
        'fecha_cierre_inscripcion': '2026-12-31',
        'estado': 'borrador',
    }, follow=True)
    
    # Check if created
    if response.status_code == 200:
        if Convocatory.objects.filter(codigo='QA-TEST-2026').exists():
            print("✓ Convocatoria created successfully")
            conv = Convocatory.objects.get(codigo='QA-TEST-2026')
            print(f"  - Nombre: {conv.nombre}")
            print(f"  - Código: {conv.codigo}")
            print(f"  - Estado: {conv.estado}")
            return conv
        else:
            print("✗ Convocatoria not found after creation")
            print(f"  Response status: {response.status_code}")
    else:
        print(f"✗ Create failed: {response.status_code}")
    return None


def test_wizard_form(client, conv):
    """Test wizard form for application"""
    print("\n=== TEST 5: Wizard FUI Form ===")
    
    # First publish the convocation
    if conv and conv.estado == 'borrador':
        conv.estado = 'publicada'
        conv.save()
        print(f"✓ Convocation published: {conv.estado}")
    
    # Create a Solicitud (application) for testing
    from django.contrib.auth import get_user_model
    User = get_user_model()
    from apps.applications.models import Solicitud
    
    user = User.objects.get(email='test@fodejas.gov.co')
    
    # Check if we already have a solicitud
    solicitud = Solicitud.objects.filter(
        convocatoria=conv,
        aspirante=user
    ).first()
    
    if not solicitud:
        # Create one
        solicitud = Solicitud.objects.create(
            convocatoria=conv,
            aspirante=user,
            estado=Solicitud.Estado.BORRADOR,
            radicado=f"FODEJAS-TEST-{conv.codigo}",
            datos_personales={'nombre': 'Test', 'municipio': 'san_andres'},
            current_step=1
        )
        print(f"✓ Created test Solicitud: {solicitud.radicado}")
    
    # Access wizard
    print(f"  Solicitud UUID: {solicitud.uuid}")
    response = client.get(f'/applications/{solicitud.uuid}/wizard/')
    print(f"  Wizard URL response: {response.status_code}")
    
    if response.status_code == 200:
        print("✓ Wizard page loads")
        # Check wizard fields
        content = response.content.decode()
        if 'wizard' in content.lower():
            print("✓ Wizard content present")
    elif response.status_code == 302:
        # Redirects to login
        print("✗ Wizard requires login")
    elif response.status_code == 404:
        print("✗ Wizard URL not found - check UUID")


def main():
    print("=" * 50)
    print("FODEJAS QA Tests - Formularios de Convocatoria")
    print("=" * 50)
    
    # Test login
    client = test_login()
    if not client:
        print("\n✗ Cannot proceed without login")
        return
    
    # Test list
    test_convocatoria_list(client)
    
    # Test form
    test_convocatoria_create_form(client)
    
    # Create convocation
    conv = test_create_convocatoria(client)
    
    # Test wizard
    test_wizard_form(client, conv)
    
    print("\n" + "=" * 50)
    print("QA Tests Complete")
    print("=" * 50)


if __name__ == '__main__':
    main()
