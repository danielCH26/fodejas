# Catálogos del Dominio (apps/core)

Este módulo contiene los catálogos paramétricos del dominio FODEJAS.

## Modelos

| Modelo | Descripción |
|--------|-------------|
| `Estrato` | Estrato socioeconómico (1-6) |
| `GrupoSisben` | Grupo SISBÉN (A-D) |
| `Etnia` | Etnia/pertinencia étnica |
| `MunicipioIsla` | Municipio/Isla del Archipiélago |
| `NivelFormacion` | Nivel de formación |
| `ModalidadApoyo` | Modalidad de apoyo (crédito, beca, préstamo) |
| `TipoIes` | Tipo de IES |
| `TipoDocumento` | Tipo de documento de identidad |
| `EstadoDocumento` | Estado de validación de documento |
| `CausalTerminacionConvenio` | Causal de terminación de convenio |

## Cómo agregar valores

Los catálogos se cargan vía **data migration**, no fixtures.

```bash
python manage.py makemigrations core --name seed_<catalog>
```

En la migración usar `RunPython` con `get_or_create`:

```python
from django.db import migrations

def seed_estratos(apps, schema_editor):
    Estrato = apps.get_model('core', 'Estrato')
    for code, name in [('1', 'Estrato 1'), ...]:
        Estrato.objects.get_or_create(
            codigo=code,
            defaults={'nombre': name, 'orden': int(code)}
        )

def reverse_seed(apps, schema_editor):
    Estrato = apps.get_model('core', 'Estrato')
    Estrato.objects.all().delete()
```

## ⚠️ Advertencia

**Nunca modificar catálogos vía admin en producción.** Los catálogos son datos de referencia que deben ser consistentes entre entornos. Usar migrations para cambios.
