# Runbook — Migración de datos legacy (CHG-099)

> Documento operativo. Referencia:
> `openspec/changes/CHG-099-migration/proposal.md`,
> `docs/migrations/data-schemas.md`.

## Pre-requisitos

- Acceso al staging PostgreSQL (no a producción).
- Variable de entorno `LEGACY_DATA_SALT` configurada en el
  entorno de staging (32+ caracteres aleatorios).
- Acceso a la carpeta `/secure/legacy-data/` del drive compartido
  de la Secretaría (NO en el repo).
- Aprobación escrita del Oficial de Protección de Datos para
  ejecutar esta corrida (registrada en el ticket de migración).

## Paso 1 — Recibir los archivos del operador

El operador entrega los 5 CSVs en `/secure/legacy-data/`:

```
/secure/legacy-data/
├── convocatorias.csv
├── solicitudes.csv
├── usuarios_legacy.csv
├── actos_legacy.csv
└── listados_legacy.csv
```

Los archivos DEBEN respetar los headers en `data-schemas.md`. Si
faltan columnas o hay columnas extra, abortar inmediatamente y
solicitar archivos correctos.

## Paso 2 — Anonimización previa (FUERA del repo)

**CRÍTICO**: este paso ocurre en una máquina de pre-procesamiento
que NO toca el repo. Los CSVs anonimizados se escriben a una
ubicación temporal (`/tmp/anon-legacy/`).

```bash
# En una máquina con los datos crudos pero SIN acceso al repo:
python scripts/anonymize_legacy.py \
    --input /secure/legacy-data/ \
    --output /tmp/anon-legacy/ \
    --salt-env LEGACY_DATA_SALT
```

El script `scripts/anonymize_legacy.py` (provisto en este change)
aplica `sha256(value + salt)[:12]` a todos los campos PII según
`data-schemas.md`.

**Verificar** que ningún CSV anonimizado contiene:
- emails con formato `@example.com`, `@gmail.com`, etc.
- documentos con secuencias de 7-10 dígitos.
- teléfonos con 10 dígitos.

```bash
grep -rE "@[a-z]+\\.[a-z]+" /tmp/anon-legacy/ && echo "FAIL: PII found" || echo "OK"
grep -rE "[0-9]{7,10}" /tmp/anon-legacy/ | head && echo "FAIL: possible PII" || echo "OK"
```

## Paso 3 — Montar el volumen read-only

```bash
# En el servidor de staging:
mkdir -p /srv/migration/anon-legacy
mount --bind -o ro /tmp/anon-legacy /srv/migration/anon-legacy
```

Verificar permisos:
```bash
ls -la /srv/migration/anon-legacy
-r--r--r-- ... convocatorias.csv
...
```

## Paso 4 — Dry-run

```bash
cd /srv/app  # working directory de la app
python manage.py migrate_legacy_data \
    --source=/srv/migration/anon-legacy/ \
    --dry-run
```

El reporte debe incluir:
- Conteo por modelo (esperado: N convocatorias, M solicitudes, K actos, etc.)
- Validación de schemas (todos PASS)
- Validación de FKs (todas resueltas)
- Validación de PII (todas PASS)

**Si hay errores**, abortar y reportar. NO continuar al paso 5.

## Paso 5 — Aplicar

```bash
python manage.py migrate_legacy_data \
    --source=/srv/migration/anon-legacy/
```

Verificar exit code = 0.

## Paso 6 — Auditar

```bash
# Conteos finales:
python manage.py shell -c "
from apps.convocatories.models import Convocatory
from apps.applications.models import Solicitud
from apps.accounts.models import CustomUser
from apps.governance.models import ActoAdministrativo, ListadoDefinitivo
print('Convocatorias:', Convocatory.objects.count())
print('Solicitudes:', Solicitud.objects.count())
print('Usuarios:', CustomUser.objects.count())
print('Actos:', ActoAdministrativo.objects.count())
print('Listados:', ListadoDefinitivo.objects.count())
"

# Verificar idempotencia (re-correr no debe duplicar):
python manage.py migrate_legacy_data \
    --source=/srv/migration/anon-legacy/
python manage.py shell -c "
from apps.convocatories.models import Convocatory
print('Post-re-run Convocatorias:', Convocatory.objects.count())
"
# Debe ser el mismo número que antes del re-run.

# Verificar que no hay PII en la DB:
python manage.py shell -c "
from apps.accounts.models import CustomUser
for u in CustomUser.objects.all()[:5]:
    print('doc:', u.documento, 'email:', u.email)
"
# Los documento y email DEBEN ser hashes de 12 chars hex, NO
# documentos reales.
```

## Paso 7 — Limpiar y documentar

```bash
# Borrar el mount temporal:
umount /srv/migration/anon-legacy
rm -rf /tmp/anon-legacy/

# Documentar la corrida en CHG-099/apply-progress.md (anexar
# tabla con timestamp + conteos).

# Cerrar el ticket de migración.
```

## Checklist de anonimización

Antes de marcar la migración como completada, el operador DEBE
confirmar cada item:

- [ ] Ningún CSV en `/secure/legacy-data/` quedó sin anonimizar.
- [ ] `/tmp/anon-legacy/` se borró después de la corrida.
- [ ] El ticket del Oficial de Protección de Datos quedó cerrado
      con la confirmación escrita de que la base de staging quedó
      con datos anonimizados (no PII).
- [ ] La variable `LEGACY_DATA_SALT` quedó registrada en el vault
      del proyecto (NO en el repo).
- [ ] El log de auditoría (audit signal CHG-801) tiene un evento
      `MIGRATION_LEGACY_DATA` con timestamp, operador, conteos.

Si alguno de estos items falla, NO se considera la migración
exitosa y se aborta el despliegue.
