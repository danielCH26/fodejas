# Feature: Go-live readiness (post backlog)

> Programa ODD de puesta a punto tras el cierre del backlog post-MVP.
> Base: docs/ops/05-known-gaps.md (10 gaps, 3 bloqueantes) + hallazgos de PR.
> Principio: desbloquear pipeline de PRs → bloqueantes go-live → deuda.

## Orden del programa

1. **Fix `/api/audit/verify/` + descripciones de PR** — rama
   `chore/audit-verify-url` desde master. URL faltante (hallazgo runbooks)
   con test-first + `odd/pr-descriptions.md` con las 6 descripciones listas.
   - [x] 1.1 test API verify para admin (RED)
   - [x] 1.2 registrar ruta en apps/audit/urls.py (GREEN)
   - [x] 1.3 odd/pr-descriptions.md (6 PRs: fix, 504, 505, 506, 507, audit-url)
   - Evidencia: `c8ecf9b` — fix creció a un clúster de 5 bugs 500
     pre-existentes en páginas HTML de audit (urls sin namespace,
     login_url inexistente, load faltante, filtro no defensivo);
     7 tests de ruta/render; suite 522✓ en la rama
2. **Ops hardening** — rama `chore/ops-hardening` desde master, 4 commits:
   - [ ] 2.1 backup-exporter (textfile collector + container en compose)
   - [ ] 2.2 pg_stat_statements (postgres.conf + extension + alerta viva)
   - [ ] 2.3 MinIO lifecycle policy (init script en compose)
   - [ ] 2.4 collectstatic/compilemessages en CI
3. **Media serving** 🔴 bloqueante go-live — rama `chore/media-serving`
   (o feat/ con mini-OpenSpec si el delta lo amerita). Explorar
   django-storages/STORAGES y el plan .kilo (MinIO dev, volúmenes prod).
   Decisión de producto si hay ambigüedad real.
   - [x] 3.1 exploración + decisión (bucket privado + URLs firmadas, Ley 1581;
     MinIO path-style; prefijo media/; roadmap.md §INF-008 autoritativo)
   - [x] 3.2 implementación + tests de URL de anexos
     - STORAGES dict + AWS vars en config/settings.py ✓
     - docker/minio-init/lifecycle.sh (bucket + versioning + lifecycle) ✓
     - apps/core/tests/test_media_storage.py: 12✓ 1skipped (host sin
       django-storages; pasa en Docker) — ver evidencia abajo
     - NOTA: 6 tests en governance/ usan FileField sin @override_settings;
       requieren django-storages instalado o su propio STORAGES override;
       no son tests de URL de anexos (ver docs/ops/05-known-gaps.md)
4. **Deuda i18n interna** — ejecutada por pedido del usuario ("sigue").
   - [x] 4.1 33 templates internos marcados + TextChoices raw wrapped
     (treasury 7 + academic_tracking 11 labels) en chore/i18n-internal
     (apilada sobre feat/CHG-507); +345 msgids (816 total); regresión
     527✓. Errores API DRF también cerrados (047432e en
     chore/i18n-api-errors: 12 strings, 828 traducciones). Restante:
     2 strings JS (scoring, assign_role) — tickets futuros
5. **Acciones del usuario (fuera del repo)** — recordatorios, no tareas:
   - push + 5 PRs + merges (superset en odd/tasks)
   - primera prueba de restore en staging (protocolo docs/ops/02)
   - aprobación institucional RTO/RPO + SLOs
   - borrar stash@{0} y rama local obsoleta feat/CHG-501-sessions

## Reglas

- Ramas nuevas desde master; work-unit commits por tarea.
- Test-first donde aplique; ops config = verificación funcional.
- docs/ops/05-known-gaps.md se actualiza por PR cuando un gap se cierra.

## Evidencia

- 2026-10-12 — Programa creado; ver estado git en turnos previos.
