#!/usr/bin/env python
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.models import ActivosManager, CatalogoDominio

print(f"CatalogoDominio: {CatalogoDominio}")
print(f"CatalogoDominio.__dict__.keys(): {list(CatalogoDominio.__dict__.keys())}")

# Check if 'objects' is in __dict__
print(f"'objects' in CatalogoDominio.__dict__: {'objects' in CatalogoDominio.__dict__}")
print(f"'activos' in CatalogoDominio.__dict__: {'activos' in CatalogoDominio.__dict__}")

# Try to access them directly
try:
    objects_attr = CatalogoDominio.__dict__['objects']
    print(f"CatalogoDominio.__dict__['objects']: {objects_attr}")
    print(f"type(CatalogoDominio.__dict__['objects']): {type(objects_attr)}")
except KeyError:
    print("'objects' not in __dict__")

try:
    activos_attr = CatalogoDominio.__dict__['activos']
    print(f"CatalogoDominio.__dict__['activos']: {activos_attr}")
    print(f"type(CatalogoDominio.__dict__['activos']): {type(activos_attr)}")
    print(f"isinstance(activos_attr, ActivosManager): {isinstance(activos_attr, ActivosManager)}")
except KeyError:
    print("'activos' not in __dict__")
