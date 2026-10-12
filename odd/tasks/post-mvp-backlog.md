# Feature: Post-MVP Backlog (CHG-504..507 + higiene)

> Programa de trabajo post-MVP para FODEJAS. Orden decidido por el
> orquestador (autorización del usuario: "organiza el orden como quieras").
> Clone de trabajo: `C:/Users/danie/Downloads/FodejaApp/fodejas`, master @ `54467cf`.

## Orden del programa

1. **Higiene JD ledger** — items menores del Judgment Day (sin CHG propio si no
   tocan specs; si tocan contrato, mini-change OpenSpec).
   - [x] `revisado_por` en impedimentos → `e04cab2` (campo ya existía;
     bug: `votar_impedimento()` nunca lo asignaba)
   - [x] `_add_working_days` retroactivo → `e04cab2` (ya soportaba días
     negativos; se agregaron tests que lo documentan)
   - [x] Tests de edge: quórum 1-miembro, 0-votos → `e04cab2`
     (6 tests nuevos en `test_sessions.py`; 0 votos → RECHAZADO)

   Verificación: 522 passed, 8 skipped (suite completa, sqlite),
   `manage.py check` ✓, `makemigrations --check` ✓. Rama `fix/jd-ledger-minors`.
   Nota: falla ambiental del guard `test_stubs_removed` resuelta eliminando
   `apps/psychosocial/__pycache__` huérfano (artefacto local pre-CHG-806).
2. **CHG-504 — Portal de transparencia** (CAP-021) — mayor valor público.
   - [x] OpenSpec: proposal + tasks + delta → `8c9696c`
   - [x] Unidad A (API JSON + selectores PII-safe) → `70ea9b7` (21 tests)
   - [x] Unidad B (portal HTML + nav) → `888eb2f` (20 tests)
   - Rama `feat/CHG-504-portal-transparencia`; suite 557✓/8 skip;
     check ✓; migraciones ✓; template-safety ✓ (cero PII)
   - Desviaciones legítimas: estado real `EN_INSCRIPCION` (no `ABIERTA`);
     filtro año aplica a ejecución presupuestal (demás secciones
     acumuladas, documentado en spec)
   - **Hallazgo PRE-EXISTING**: proyecto sin config de media
     (`MEDIA_URL`/`MEDIA_ROOT`/serve) — links PDF del portal rotos hasta
     configurar; afecta a todos los FileField (actos, actas,
     comprobantes). Backlog: infra media serving.
   - Pendiente: 6.4 revisión manual incógnito (usuario, al desplegar);
     5.6 PostgreSQL vía CI al push
3. **CHG-505 — Export auditoría externa** (CAP-028) — paquete verificable
   de la bitácora hash-chain.
4. **CHG-506 — Estudio de impacto** (CAP-027) — reportes de impacto.
5. **CHG-507 — Multilenguaje** (CAP-030) — al final: es transversal y cada
   feature nueva agrega templates a traducir.
6. **Runbooks/DRP** (INF-011/012/015) — docs operativos, cuando el código
   esté estable.

## Reglas del programa

- OpenSpec obligatorio para cada CHG: `proposal.md` + `tasks.md` + delta
  en `openspec/changes/<id>/` antes de escribir código del feature.
- Work-unit commits por tarea, Conventional Commits con `CHG-NNN`/`CAP-NNN`.
- Test-first donde aplique (scoring, estados, monetario/plazos: no negociable).
- Sin PII, sin integraciones externas, sin inventar normativa.
- Suite completa verde (sqlite) antes de cerrar cada feature.

## Evidencia

- 2026-10-12 — Programa creado; clone resincronizado a master `54467cf`
  (commit base del programa). Stash de churn viejo pendiente de borrar:
  `git stash list` → "stale black-formatting churn before sync to master 54467cf".
