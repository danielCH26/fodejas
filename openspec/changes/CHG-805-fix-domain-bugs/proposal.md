# CHG-805 — Defectos de dominio (listado, scoring, RBAC, apelaciones, normativa)

## Contexto

La auditoría completa del 2026-09-05 (`docs/audits/initial-audit.md`
AUD-005, AUD-006, AUD-007, AUD-008, AUD-009, AUD-011 y
`docs/audits/extended-audit.md` AUD-007 reclasificado a CRITICAL)
detectó seis defectos de dominio que no son systemic pero
deben arreglarse antes de la primera convocatoria:

- **AUD-005** — `apps/governance/services/listado.py` referencia
  `Convocatory.Estado.RESULTADOS_DEFINITIVOS` (no existe, es
  `DEFINITIVA`) y `puntaje.puntaje_merito` / `puntaje_residencia`
  (no existen en `PuntajeTotal`, que tiene `excelencia`,
  `academico`, `socioeconomico`). El `try/except Exception: pass`
  traga el `AttributeError`.
- **AUD-007 (reclasificado CRITICAL)** —
  `apps/scoring/services/scoring_service.py:34-82`
  `calcular_puntaje_total` hace `get_or_create` + `save` sin
  `@transaction.atomic` ni `select_for_update`. Es alcanzable desde
  views (AUD-007 → CRITICAL). Carrera que puede producir
  `puntaje_total` con valores inconsistentes.
- **AUD-006** — `apps/accounts/permissions.py:23-80` define la clase
  `HasRole` dos veces en el mismo módulo. Python usa la segunda
  definición; la primera (con helpers `has_role`/`has_any_role`/
  `has_all_roles`) es código muerto.
- **AUD-008** — Tres views hacen `request.user.groups.filter(name=...)`
  directamente: `apps/applications/views.py:363`, `apps/scoring/views.py:25`,
  `apps/scoring/views.py:158`. Bypassean la capa `Role` introducida
  en CHG-101.
- **AUD-009** — `apps/claims/permissions.py:65-72`
  `CanCreateApelacion.has_object_permission` importa `can_apelar`
  que **no existe** en `apps/claims/services/apelaciones.py`. La
  clase no está wired a una view todavía, pero cualquier CHG que
  la use va a explotar en runtime.
- **AUD-011** — `apps/convocatories/domain/normativa.py:42, 47, 59, 65`
  tiene placeholders `"Art. ... Decreto 0372/2025"` en los plazos
  `beneficio_5_semestres`, `beneficio_10_semestres`,
  `tesoreria_5_dias`, `exoneracion_30_dias`. AGENTS.md §6 regla 4
  prohíbe inventar normativa; el placeholder es la violación más
  blanda posible pero sigue siendo una violación.

## Capacidades afectadas

- **CAP-005** (Scoring — AUD-007).
- **CAP-008** (Resultados definitivos — AUD-005).
- **CAP-001** (RBAC — AUD-006, AUD-008).
- **CAP-006/007** (Reclamaciones / Apelaciones — AUD-009).
- **CAP-009/010/013/014/015/016** (varios plazos — AUD-011).

## Reglas de negocio afectadas

- `AGENTS.md` §6 regla 4 (no inventar normativa; citar siempre).
- `AGENTS.md` §6 regla 5 (no saltarse pruebas en scoring,
  transiciones de estado, generación de actos administrativos).
- `AGENTS.md` §6 regla 6 (no mover lógica de negocio a vistas).

## Cambios propuestos

### Delta en `specs/scoring/spec.md`

#### MODIFIED — § Atomicidad del cálculo de puntaje

`calcular_puntaje_total` **SHALL** ejecutarse dentro de
`@transaction.atomic` y usar
`PuntajeTotal.objects.select_for_update().get_or_create(...)`. El
acceso desde views de scoring **SHALL** propagar la transacción.

### Delta en `specs/governance/spec.md`

#### MODIFIED — § Generación del listado definitivo

`apps/governance/services/listado.py` **SHALL** referenciar
`Convocatory.Estado.DEFINITIVA` (no `RESULTADOS_DEFINITIVOS`) y
los campos `puntaje_excelencia`, `puntaje_academico`,
`puntaje_socioeconomico` (no `puntaje_merito` /
`puntaje_residencia`). El `try/except Exception: pass` alrededor
del cambio de estado **SHALL** reemplazarse por manejo explícito
con `Convocatory.DoesNotExist` y registro en audit log si el
estado no puede transicionarse.

### Delta en `specs/accounts/spec.md`

#### MODIFIED — § Clase `HasRole`

`apps/accounts/permissions.py` **SHALL** contener una sola
definición de `HasRole`. Los helpers `has_role`,
`has_any_role`, `has_all_roles` **SHALL** migrar a funciones
de módulo o conservarse como métodos en la clase única.

#### MODIFIED — § Chequeos de rol en vistas

Toda view que valide rol de usuario **SHALL** usar
`apps.accounts.permissions_mixin.PermissionMixin._has_role(user,
"CODE")` en lugar de `request.user.groups.filter(name=...).exists()`.
Las llamadas directas a Django `Group` quedan prohibidas para
chequeos de rol (solo se permiten para checks de `is_superuser` o
`is_staff`).

### Delta en `specs/claims/spec.md`

#### MODIFIED — § Helper de elegibilidad de apelación

`CanCreateApelacion.has_object_permission` **SHALL** invocar
`validar_apelacion(obj, request.user)` (que ya existe y devuelve
la tupla `(is_valid, error_message)` correcta) en lugar del
inexistente `can_apelar`. Si en el futuro se quiere un helper
`can_apelar` semánticamente distinto, se renombra
`validar_apelacion` a `can_apelar` y se actualizan los call sites.

### Delta en `specs/convocatory-engine/spec.md`

#### MODIFIED — § Catálogo de plazos normativos

`apps/convocatories/domain/normativa.py` **SHALL** declarar los
plazos `beneficio_5_semestres`, `beneficio_10_semestres`,
`tesoreria_5_dias`, `exoneracion_30_dias` con la cita explícita
del artículo del Decreto 0372/2025 (no placeholders). Las citas
se obtienen del decreto oficial — si el equipo legal no las
confirma, se deja explícito en el código que requieren revisión.

### Cambios concretos

1. `apps/scoring/services/scoring_service.py` — wrap
   `calcular_puntaje_total` en `@transaction.atomic`, usar
   `select_for_update().get_or_create(...)`.
2. `apps/governance/services/listado.py` — cambiar referencias a
   `Convocatory.Estado.DEFINITIVA` y campos reales de `PuntajeTotal`.
3. `apps/accounts/permissions.py` — eliminar la primera definición
   de `HasRole` (la de helpers). Mantener solo la segunda
   (con `__init__`). Si se necesitan los helpers como funciones,
   extraerlos a funciones de módulo (`has_role`, `has_any_role`,
   `has_all_roles`).
4. `apps/applications/views.py`,
   `apps/scoring/views.py` — reemplazar 3 chequeos directos de
   `groups.filter(name=...)` por llamadas al mixin de permisos.
5. `apps/claims/permissions.py:65-72` — cambiar `can_apelar` →
   `validar_apelacion`.
6. `apps/convocatories/domain/normativa.py:42, 47, 59, 65` —
   reemplazar placeholders. Si el equipo legal no confirma
   todavía, documentar como `articulo="TBD - Decreto 0372/2025 -
   requiere revisión legal"` y abrir un issue.

## Criterios de aceptación

- [ ] Test de listado: `generar_listado_definitivo(convocatoria)` con
      puntajes preexistentes no lanza `AttributeError`. La
      convocatoria transiciona a `DEFINITIVA`. Test cubre campos
      reales del modelo `PuntajeTotal`.
- [ ] Test de scoring concurrente: 2 hilos lanzan
      `calcular_puntaje_total` en la misma `Solicitud` → uno gana,
      el `puntaje_total` final es consistente (no negativo, no
      fuera de rango, sin componentes stale).
- [ ] Test de RBAC: solo queda una definición de `HasRole` en
      `apps/accounts/permissions.py`. Las 3 views de
      AUD-008 usan `_has_role()` del mixin.
- [ ] Test de apelaciones: una view wired con
      `permission_classes = [CanCreateApelacion]` no lanza
      `ImportError`.
- [ ] Test de normativa: las 4 entradas de plazo tienen una
      cadena de artículo no-vacía (no `"Art. ..."`).
- [ ] `pytest apps/scoring apps/governance apps/claims
      apps/accounts apps/convocatories` corre limpio.

## Pruebas

- `apps/scoring/tests/test_scoring_atomic.py` — race condition test.
- `apps/governance/tests/test_listado_definitivo.py` — generación
  end-to-end con datos sintéticos.
- `apps/accounts/tests/test_permissions_unique_hasrole.py` — solo
  una definición.
- `apps/claims/tests/test_appeal_permission.py` — CanCreateApelacion
  resuelve.
- `apps/convocatories/tests/test_normativa_catalog.py` — verifica
  que ninguna entrada tiene `"Art. ..."`.

## Riesgos y Fuera del alcance

- **Riesgo**: los chequeos `_has_role(user, "CODE")` hacen una query
  por request. Si llegan a ser cuello de botella, se cachea con
  `request.user._role_cache`. Queda fuera del alcance.
- **Riesgo**: si el equipo legal no confirma los artículos,
  reemplazamos por `TBD - Decreto 0372/2025` y abrimos issue.
  No bloqueamos el deploy por esto.
- **Fuera del alcance**:
  - No se rediseña el modelo `PuntajeTotal` (no cambiamos campos,
    solo corregimos referencias).
  - No se agrega vista de listado para Junta (queda en otro
    change si surge la necesidad).
  - No se migra el catálogo histórico de normativas.

## Referencias

- `docs/audits/initial-audit.md` §3.2 AUD-005, §3.3 AUD-006/008/009,
  §3.4 AUD-011, §3.4 AUD-007 (WARNING).
- `docs/audits/extended-audit.md` §5.2 AUD-007 reclasificado a
  CRITICAL.
- `AGENTS.md` §6 reglas 4, 5, 6.
- `Decreto 0372/2025` Arts. 11, 14, 15, 16, 17 (citados
  tentativamente — confirmar con legal).
