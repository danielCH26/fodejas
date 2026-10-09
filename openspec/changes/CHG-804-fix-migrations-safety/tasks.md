# Tasks — CHG-804 Seguridad de migraciones (expand/contract + backfill UUID en PKs)

> Referencia: `proposal.md`. Plantilla según `AGENTS.md` §4.

## 1. Migración de backfill de UUIDs en `accounts` (data-only)

- [x] Crear `apps/accounts/migrations/0008_backfill_uuids_customuser_role.py`.
- [x] Encadenar con `dependencies = [("accounts", "0007_alter_role_id")]`.
- [x] Implementar `backfill_customuser_uuid(apps, schema_editor)`:
  - [ ] `CustomUser = apps.get_model("accounts", "CustomUser")`.
  - [ ] Detectar PK actual vía `CustomUser._meta.pk.get_internal_type()`.
  - [ ] Si el PK ya es `UUIDField` → noop (idempotencia).
  - [ ] Iterar `CustomUser.objects.all()` y reasignar `pk` con `uuid.uuid5(NAMESPACE_URL, f"customuser:{old_pk}")` solo si `pk` no es instancia de `uuid.UUID`.
  - [ ] Persistir con `user.save(update_fields=["id"])` (no tocar campos PII).
- [x] Implementar `backfill_role_uuid(apps, schema_editor)` análogo para `Role` (namespace key `"role:{old_pk}"`).
- [x] `reverse_code` documentado como `noop` con comentario explicando por qué (sin tabla de mapeo no es seguro).
- [x] `operations = [migrations.RunPython(forward, reverse)]` — sólo data, sin `state_operations`.

## 2. Migración de backfill de UUIDs en `convocatories` (data-only)

- [x] Crear `apps/convocatories/migrations/0003_backfill_uuids_convocatory.py`.
- [x] Encadenar con `dependencies = [("convocatories", "0002_alter_convocatory_id")]`.
- [x] `backfill_convocatory_uuid(apps, schema_editor)` análogo a §1, con `Convocatory = apps.get_model("convocatories", "Convocatory")` y namespace key `"convocatory:{old_pk}"`.
- [x] `reverse_code` como `noop` documentado.
- [x] `operations = [migrations.RunPython(forward, reverse)]`.

## 3. Documentación `docs/migrations/expand-contract.md`

- [x] Crear directorio `docs/migrations/`.
- [x] Crear `docs/migrations/expand-contract.md` con secciones:
  - [ ] "Por qué expand/contract" (zero-downtime, reversible, INF-014).
  - [ ] "Receta en 4 pasos" (expand → backfill → swap → contract).
  - [ ] "Plantilla de migración" (esqueleto `AddField`/`RunPython`/`AlterField`/`RemoveField`).
  - [ ] "Ejemplo guiado" sobre `accounts.CustomUser`.
  - [ ] "Historia de migraciones destructivas" (las tres de 2026-07-17/18 con tabla).
  - [ ] "Cómo revertir una migración UUID fallida" (forward-only repair con namespace alternativo).
  - [ ] "Estado esperado por environment".
  - [ ] Enlace a `roadmap.md §4.1 INF-014` y a `docs/audits/extended-audit.md` §7, §8.2 AUD-019.

## 4. CI guard `.github/workflows/migrations-safety.yml`

- [x] Crear `.github/workflows/migrations-safety.yml`.
- [x] Disparar en `pull_request` y `push` a `main`/`develop`.
- [x] Job `migrations-safety` con:
  - [ ] `actions/setup-python@v5` (3.11).
  - [ ] `pip install -e ".[dev]"`.
  - [ ] `python manage.py makemigrations --check --dry-run` (no debe generar migraciones nuevas).
  - [ ] `grep` heurístico: listar los últimos 5 archivos en `apps/*/migrations/*.py` ordenados por nombre, buscar `AlterField` + `primary_key=True` sin migración de backfill posterior; fallar si lo encuentra.
  - [ ] Subir el diff/log como artefacto en caso de fallo (`actions/upload-artifact@v4`).

## 5. Anotación de migraciones destructivas existentes (sólo comentarios)

- [x] Agregar bloque de comentario al inicio de:
  - [ ] `apps/accounts/migrations/0006_alter_customuser_id.py`.
  - [ ] `apps/accounts/migrations/0007_alter_role_id.py`.
  - [ ] `apps/convocatories/migrations/0002_alter_convocatory_id.py`.
- [x] El comentario referencia la nueva migración de backfill y `docs/migrations/expand-contract.md`.
- [x] **NO** modificar `operations`, `dependencies` ni el cuerpo ejecutable. Solo añadir líneas de comentario al tope del archivo.

## 6. Tests

### 6.1 `apps/accounts/tests/test_migrations_uuid.py`

- [x] Test de la función de backfill: invocar `backfill_customuser_uuid` y `backfill_role_uuid` con un app registry sintético (sin tocar la DB real).
- [x] Test de idempotencia: crear un `CustomUser` con PK UUID (estado actual del modelo), llamar dos veces consecutivas y verificar que no se modifica ni lanza.
- [x] Test de no-PII: ninguna fixture debe contener emails, documentos o nombres reales.

### 6.2 `apps/convocatories/tests/test_migrations_uuid.py`

- [x] Análogo a 6.1 para `Convocatory` y la función `backfill_convocatory_uuid`.

### 6.3 Reversibilidad

- [x] Test que llame `migrate accounts 0007` (estado pre-backfill) y luego `migrate accounts 0008` (forward); verificar que ambas direcciones dejan los datos consistentes.
- [x] Verificar que correr la migración dos veces seguidas no rompe.

## 7. Verificación final

- [x] `python -c "import ast; ast.parse(...)"` sobre las dos migraciones nuevas.
- [x] `python -m pytest apps/accounts/tests/test_migrations_uuid.py apps/convocatories/tests/test_migrations_uuid.py -x`.
- [x] `python manage.py makemigrations --check --dry-run` (debe pasar sin generar nuevas migraciones).

## 8. Hand-off

- [x] Escribir `openspec/changes/CHG-804-fix-migrations-safety/apply-progress.md` con resumen, archivos tocados, comandos de verificación y resultados.
