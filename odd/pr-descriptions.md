# PR Descriptions — Go-live readiness batch

> Listas para pegar al crear cada PR (base: `master`).
> Orden de merge recomendado: 1 → 2 → 3 → 4 → 5 → 6.
> En cada merge de 2..5, resolver conflicto add/add en
> `odd/tasks/post-mvp-backlog.md` tomando el **superset** (el más nuevo).

---

## 1. `fix/jd-ledger-minors`

**Título**: `fix(governance): set revisado_por on impedimento review + session edge tests (CHG-501, CHG-502)`

**Resumen**: Cierra 3 items menores del ledger de Judgment Day: (a) `votar_impedimento()` nunca asignaba `revisado_por` (el campo existía; ahora registra al actor que completa la mayoría), (b) tests que documentan el soporte retroactivo de `_add_working_days`, (c) tests de edge de sesiones: quórum con exactamente 1 miembro votante y cierre de punto con 0 votos (→ RECHAZADO).

**Testing**: +6 tests (`apps/governance/tests/test_sessions.py`). Suite 522✓ sqlite.

**Notas**: Independiente de las demás; puede mergearse primero.

---

## 2. `feat/CHG-504-portal-transparencia`

**Título**: `feat(CHG-504): public transparency portal — HTML + JSON API (CAP-021)`

**Resumen**: Portal público `/transparencia/` (landing con KPIs, actos publicados paginados con PDF, convocatorias, estadísticas por año/estado) + API JSON pública `/api/transparencia/` (AllowAny, read-only). Selectores con whitelist explícita de campos — cero PII (Ley 1581/2012), solo actos `PUBLICADO`. Nav pública en `base.html`. OpenSpec completo en `openspec/changes/CHG-504-portal-transparencia/`.

**Testing**: +41 tests (selectores, API anónima, HTML anónima, PII-negativos, paginación, sólo-PUBLICADO). Suite 537✓. Seguridad: read-check PASS (sin email/nombre/documento en ninguna respuesta).

**Notas**: Desglose IES/municipio deferido a CHG-506. Auditoría de lecturas públicas: decisión abierta para CHG-505.

---

## 3. `feat/CHG-505-external-audit`

**Título**: `feat(CHG-505): external audit export with verifiable manifest headers (CAP-028)`

**Resumen**: `GET /api/audit/export/?format=csv|jsonl` (§14.3) con streaming, eventos exportados **verbatim** (verificabilidad del hash-chain) y manifiesto en headers: `X-Audit-Export-SHA256`, `X-Audit-Chain-Valid/Head/Break`, `X-Audit-Generated-At`. Permiso nuevo `IsAuditExporter` (R-ADMIN/R-CONTROL/R-AUDITOR) sin tocar `IsAuditViewer`. Snapshot clamp garantiza `sha256(body)==header` bajo concurrencia. Sello de tiempo lite; firma digital deferida a CAP-029; sin TSA (Regla 2).

**Testing**: +24 tests (permisos, formatos, verbatim round-trip, sha256, filtros, carrera). Suite 540✓ en la rama.

---

## 4. `feat/CHG-506-impact-study`

**Título**: `feat(CHG-506): impact study — denormalized IES/municipio, k=3 suppression, retorno tracking (CAP-027)`

**Resumen**: Estudio de impacto bianual: `Solicitud.ies_nombre` + `municipio_origen` (FK MunicipioIsla, SET_NULL) con backfill idempotente (`backfill_impact_fields --dry-run`), seed `seed_municipio_isla` (3 filas 1:1 con el wizard), `AcademicRecord.retorno_archipelago` con endpoint de anotación manual (audit atómico fail-closed), `ReportingService.estudio_impacto()` con supresión k=3 en desgloses por IES/municipio, `GET /api/reporting/estudio-impacto/` (REPORT_ROLES + R-CT). OpenSpec: `openspec/changes/CHG-506-impact-study/`.

**Testing**: +49 tests (backfill/seed idempotencia, montos contra fixtures, k-supresión, permisos, audit rollback). Suite 565✓ en la rama. `makemigrations --check` limpio (2 migraciones nuevas).

**Notas**: Tras merge, correr en deploy: `seed_municipio_isla` + `backfill_impact_fields`.

---

## 5. `feat/CHG-507-multilang`

**Título**: `feat(CHG-507): i18n infrastructure, language switcher and public translations (CAP-030)`

**Resumen**: Infraestructura i18n completa (`LocaleMiddleware`, `LANGUAGES` es-CO/en, `LOCALE_PATHS`), switcher ES/EN en la nav pública, `locale/{es_CO,en}` con `.po`+`.mo` commiteados y `scripts/compile_mo.py` (polib — sin gettext en dev). Piloto accounts + 22 templates públicos marcados: **471 traducciones** al inglés. Contrato de regresión: msgids byte-idénticos al español actual → es-CO renderiza igual y los tests existentes pasan sin cambios. PDFs legales excluidos; creole decisión abierta documentada. Incluye `docs/ops/` (INF-011/012/015: runbooks, DRP, monitoring, known-gaps).

**Testing**: +11 tests i18n (middleware position, switcher cookie, login en inglés, regresión es-CO, compile_mo). Suite 527✓ en la rama. `.mo` deterministas (hash idéntico entre corridas).

**Notas**: Deuda i18n documentada (templates internos, API errors, TextChoices raw). 3 msgids blocktrans con placeholders `%(var)s` corregidos (lookup real de Django).

---

## 6. `chore/audit-verify-url`

**Título**: `fix(audit): register JSON verify API and repair broken HTML surfaces`

**Resumen**: `/api/audit/verify/` servía la vista HTML; ahora sirve `AuditChainVerifyView` (JSON, IsAdminUser). Repara 500s pre-existentes en TODAS las páginas HTML de audit: nombres de url sin namespace en templates, `login_url` apuntando a `login` inexistente, `detail.html` sin `{% load audit_tags %}`, y `pretty_json` crasheando con instancias de modelo.

**Testing**: +6 tests de ruta y render (JSON payload, 401 anónimo, HTML verify/dashboard/detail). Suite 522✓ en la rama.

**Notas**: Los runbooks `docs/ops/03-incident-response.md` referencian `/accounts/audit/verify/` (HTML) y el shell — siguen válidos; el endpoint JSON ahora complementa.
