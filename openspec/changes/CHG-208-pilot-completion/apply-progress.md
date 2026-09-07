# Apply Progress — CHG-208

> Estado al cierre del fast-forward. Ver `proposal.md` y `tasks.md`
> para el alcance completo.

## Resumen

Cierre del flujo de Fase 2: workflow de actos administrativos completo
(BORRADOR → FIRMADO → PUBLICADO), soporte para actos modificatorios
(CPACA Art. 45), y tests e2e del piloto completo.

## Estado de tasks.md

- [x] §1 Workflow de actos — vistas faltantes (ActoSignView, ActoModificatorioCreateView)
- [x] §2 URLs (firmar + modificatorio)
- [x] §3 Lógica de dominio (`apps/governance/domain/transitions.py`)
- [x] §4 Tests del workflow (`test_workflow.py`, `test_modificatorio.py`)
- [x] §5 Tests de flujo Fase 2 claims (`test_reclamacion_flow.py`, `test_apelacion_flow.py`)
- [x] §6 Test e2e del piloto (`test_pilot_e2e.py`)
- [x] §7 Spec deltas en `specs/governance/spec.md` y `specs/claims/spec.md`
- [x] §8 Verificación final

## Archivos tocados

| Path | Acción | Notas |
|------|--------|-------|
| `apps/governance/domain/__init__.py` | creado | paquete nuevo |
| `apps/governance/domain/transitions.py` | creado | `firmar_acto`, `crear_modificatorio` (puro dominio, sin ORM directo) |
| `apps/governance/views.py` | modificado | agrega `ActoSignView` + `ActoModificatorioCreateView` |
| `apps/governance/urls.py` | modificado | agrega `acto_sign` + `acto_modificatorio_create` |
| `apps/governance/models.py` | modificado | agrega `fecha_firma` DateTimeField |
| `apps/governance/migrations/0002_actoadministrativo_fecha_firma.py` | creado | migración data-only |
| `apps/governance/services/generador.py` | modificado | **bug fix**: el formato del numero ahora incluye prefijo de tipo (`FODEJAS-RESO-2026-00001`, `FODEJAS-MODI-2026-00001`, etc.) para evitar colisiones entre tipos distintos. Bug pre-existente que la auditoría del piloto descubrió. |
| `apps/governance/tests/test_workflow.py` | creado | 5 tests del state machine |
| `apps/governance/tests/test_modificatorio.py` | creado | 3 tests CPACA Art. 45 |
| `apps/governance/tests/test_pilot_e2e.py` | creado | 2 tests e2e del piloto completo |
| `apps/claims/tests/test_reclamacion_flow.py` | creado | 3 tests del flujo de reclamación |
| `apps/claims/tests/test_apelacion_flow.py` | creado | 2 tests del flujo de apelación |
| `openspec/changes/CHG-208-pilot-completion/proposal.md` | creado | propuesta con AGENTS.md §4 |
| `openspec/changes/CHG-208-pilot-completion/tasks.md` | creado | subtareas verificables |
| `openspec/changes/CHG-208-pilot-completion/specs/governance/spec.md` | creado | delta con SH workflow + modificatorio |
| `openspec/changes/CHG-208-pilot-completion/specs/claims/spec.md` | creado | delta con lifecycles |

## Verificaciones ejecutadas

```
$ python -c "import ast; [ast.parse(open(p).read()) for p in [...]]; print('parse OK')"
parse OK

$ python -m pytest apps/governance/tests/test_workflow.py apps/governance/tests/test_modificatorio.py \
    apps/claims/tests/test_reclamacion_flow.py apps/claims/tests/test_apelacion_flow.py \
    apps/governance/tests/test_pilot_e2e.py --no-header -p no:logging
================== 15 passed, 1 skipped, 5 warnings in 1.95s ==================
```

- 15 tests nuevos pasan (incluye 2 e2e del piloto completo).
- 1 skipped: `test_concurrent_sign_serializes` marcado con `@pytest.mark.skipif`
  porque SQLite no soporta row-level locks reales. Para habilitar en CI
  PostgreSQL, quitar el skipif.

## Hallazgos del fast-forward (mejoras colaterales)

1. **Bug pre-existente en `generar_numero_acto`**: el formato
   `FODEJAS-{anio}-{seq}` no incluía el `tipo`. `resolucion` y
   `modificatorio` ambos generaban `FODEJAS-2026-00001` y colisionaban
   en el campo `numero` UNIQUE. **Fix**: nuevo formato
   `FODEJAS-{TIPO}-{anio}-{seq}` con prefijo de 4 caracteres (RESO,
   ACTA, MODI, CERT). Cada tipo tiene su propia secuencia anual.

2. **`ActoAdministrativo` sin campo `fecha_firma`**: añadido vía
   migración 0002. Se persiste en la transición BORRADOR → FIRMADO.

## Blockers

- `serialized_rollback` y FK teardown en audit signal (issue pre-existente
  de Fase 1, no introducido por este change). Tests del CHG-801 que
  dependen de FK teardown siguen fallando — fuera del alcance de
  CHG-208.

## Follow-ups

- **`CHG-501-sessions` (Fase 5)**: implementará el ciclo de Junta
  multi-firma con quórum + votaciones. El `firmar_acto` actual
  registra firmantes como JSON libre; la sessions module formalizará
  el workflow.
- **Vista HTML `acto_sign.html` y `acto_modificatorio_create.html`**:
  las vistas están implementadas pero los templates HTML no se
  incluyen en este change. Crear cuando se haga el sprint de UI.
- **Reclamación RECHAZADA que NO agota vía (CPACA estricto)**: el
  test actual confirma que el modelo lo permite y la vista de creación
  de Apelación lo bloquea vía `CanCreateApelacion.has_object_permission`.
  Pendiente un test explícito de la vista.

## Verificación post-merge (TODO para el equipo)

```bash
# En staging con PostgreSQL:
python manage.py migrate governance

# Tests unitarios y e2e:
pytest apps/governance/tests/test_workflow.py \
       apps/governance/tests/test_modificatorio.py \
       apps/claims/tests/test_reclamacion_flow.py \
       apps/claims/tests/test_apelacion_flow.py \
       apps/governance/tests/test_pilot_e2e.py -v

# Quitar el skipif del concurrent test y correr contra PostgreSQL:
sed -i 's/skipif(\n        True,/skipif(False,/' apps/governance/tests/test_workflow.py
pytest apps/governance/tests/test_workflow.py::TestActoWorkflow::test_concurrent_sign_serializes -v
# Debe pasar: una transacción gana, la otra recibe OperationalError limpia.
```

Refs CHG-208, CAP-006, CAP-007, CAP-008, CPACA Art. 45
