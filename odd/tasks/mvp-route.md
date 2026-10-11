# Ruta al MVP — Piloto FODEJAS

> Documento ODD de ruta. Decisiones delegadas al agente por el usuario
> (sesión 2026-10-09: «tomá vos las decisiones, continuá con ODD»).
> MVP definido como: ejecutar la convocatoria piloto «Reconocimiento a la
> Excelencia» **end-to-end sin papel hasta la orden de pago**: publicación →
> postulación FUI → validación de requisitos → scoring → reclamaciones y
> apelaciones → resultados definitivos → acto administrativo firmado →
> legalización del crédito → orden de pago a Tesorería.

## Decisiones tomadas

1. **Clon canónico**: `C:\Users\danie\Downloads\fodejas` (38 commits,
   WIP real). El clon `C:\Users\danie\Downloads\FodejaApp\fodejas` queda
   **congelado, solo lectura**: está 13 commits atrás y sus apps
   `reporting`/`psychosocial` ya no existen.
2. **CHG-301 canónico**: `openspec/changes/CHG-301-e-signature/` (40
   tareas, coincide con el WIP de `apps/legalization/`). El duplicado
   `chg-301-electronic-signature/` (21 tareas) se consolida y archiva.
3. **Orden de trabajo**: higiene primero (suite verde y trazabilidad),
   luego CHG-301 → CHG-302 → CHG-303, cierre con aceptación MVP.
4. **Push a origin**: queda como decisión explícita del usuario (hay 13
   commits locales sin subir). Los work-unit commits se hacen en ramas
   locales según convención §2.
5. **Fuera del MVP** (backlog post): CHG-304 (causales terminación),
   CHG-401 (seguimiento académico), Fases 4–5, apps `reporting` y
   `psychosocial`, runbooks/DRP (INF-011/012/015), portal de transparencia.

## Etapa 0 — Estabilización (rama `chore/hygiene-mvp`)

- [x] Arreglar `apps/claims/tests/test_migrations.py`: import inválido de
      migración (`from apps.claims.migrations import 0012_...` →
      SyntaxError) y método duplicado. **Verde: 4/4** (commit `f15d2e5`).
- [x] Suite colecciona sin errores: **314 tests, 0 errores**.
- [x] Consolidar duplicado CHG-301 (commit `33edb40`).
- [x] Conciliar checkboxes de `tasks.md` con evidencia: CHG-801–806
      completos; CHG-207 §1–§3; CHG-208 §1–§7 (commit `138b656`, `4559b15`).
- [x] `legalization/` al `.gitignore` (commit `e83f67a`).
- [x] `roadmap.md` y `CHANGES.md` actualizados con CHG-801..806.
- [x] Work-unit commits: 10 en `chore/hygiene-mvp`.

## Etapa 0.5 — Suite verde (parcial, misma rama)

Baseline verificado: **260 passed / 43 failed / 34 errors**. Tras P0:
**269 passed / 34 failed / 34 errors**. Fixes commiteados: namespaces
`accounts`/`audit` (`2b8b67b`), endpoint `/api/auth/me/` + blacklist JWT
(`938601e`), sqlite en memoria para tests (`0887ae6`), migración
`audit.0003` (`cf7e460`).

Pendiente:
- [x] 34 errores cascade **RESUELTOS de raíz** (commit `abdc9c4`):
      el contextvar del actor de auditoría (`set_actor`) se filtraba
      entre tests del mismo hilo → `AuditEvent` con `actor_id`
      inexistente. Fixture autouse resetea en cada borde. No hizo
      falta PostgreSQL ni reestructurar fixtures.
- [x] 6 fallos de `test_signer.py`: resueltos en Etapa 1.
- [x] `applications` test revisor: usaba `auth.Group` crudo en vez del
      sistema Role/UserRole de CHG-112 (`a51aebd`).
- [x] Migración pendiente `treasury.0004` sincronizada (`9811a34`).
- [ ] P2: deuda `ruff` (1.443, 1.311 auto-reparables).

**Suite: 419 passed / 8 skipped / 0 failed / 0 errors — 22–43s**
(era 260/43/34 al inicio de la sesión). Speed: hasher MD5 en tests
(`6366c3c`), treasury 117s → 10s.

## Etapa 1 — CHG-301 Firma electrónica (rama `feat/CHG-301-e-signature`)

- [x] Baseline WIP commiteado (commit `174c5db`); gitignore anclado a
      raíz (`21fac83`, arregla patrón que ignoraba `apps/legalization/`).
- [x] Bug `document.uuid` → `document.id` corregido (eran 4 sitios,
      commit `4902c89`): signer 20/20 verde.
- [x] Signers determinísticos + campo `changes` JSONField con migración
      `0002` (commits `acb6308`, `a4ac55f`); tasks.md al día (`6df9ab7`).
- [x] Lote 2 — flujo completo (commits `cf39da6`, `04965e9`,
      `e423207`, `3730ceb` + `tasks.md`): endpoints DRF
      `sign`/`verify` con permisos por rol, vistas/URLs HTMX, admin,
      `check_signer_config` (aborta `mock` fuera de dev), test e2e
      `test_e2e_create_sign_verify_audit_flow`. 41 tests verde.
- [ ] Deferrals a CHG-302: WeasyPrint (plantilla documento legal),
      firma async con Celery (MVP síncrono).
- [ ] Al pushear: partir en PRs encadenados por commits — lote 2 suma
      +1.433 líneas; cortes naturales: config-guard+admin (+296),
      vistas HTMX (+490), API DRF (+599). Usar skill chained-pr.

## Etapa 2 — CHG-302 Legalización (rama `feat/CHG-302-legalization`)

- [x] CAP-009 completo: `LegalizationService` (create_documents,
      generate_pdf con seam WeasyPrint, complete_legalization,
      cancel_document) + FSM en `domain/transitions.py` (commits
      `a82d30f`, `dacca73`); vistas proceso + menú R-JUNTA + admin
      filters (commits `9c67ad0`, `99c3069`, `250c3af`).
- [x] Auditoría desde la capa servicio + detección de tamper
      post-firma (test dedicado). 80 tests legalization verde;
      374 recolectados, 0 errores. tasks.md con 0 pendientes.
- [x] Plantillas PDF legales en español (pagaré, carta de
      instrucciones, contrato + CSS). Render real de WeasyPrint sin
      verificar en este host (GTK ausente) — validar en CI/contenedor.
- [ ] Al pushear: PRs encadenados — lote A suma +1.795 líneas
      (servicio+tests 1.035 / plantillas 760); lote B +240 (ok).
- Nota: tareas 1.x/2.3/4.3/4.4/5.1/7.1 ya las cubría CHG-301; marcadas
  pre-satisfechas con evidencia de commit.

## Etapa 3 — CHG-303 Desembolsos (rama `feat/CHG-303-disbursement`)

- [x] Dominio: doble firma (Presidente JA + Sec. Educación, sin
      autofirma), guard de 4 adjuntos normativos (pagaré, carta,
      contrato + ACTO_ADMINISTRATIVO — supuesto documentado), guard
      `LEGALIZADO` previo, amount>0, auditoría desde servicio
      (commits `56b0ade`, `ae8fe4c`, `3b817f6`).
- [x] UI: list/detail/authorize HTMX con gating por rol, URLs y menú
      (`1a098fb`); conciliación manual ya existía (CHG-802).
- [x] Tests: 46 servicio + 18 vistas; sweep VENCIDO 5 días hábiles
      probado. 427 recolectados, 0 errores. tasks.md 0 pendientes.
- [ ] Revisión: mapeo de roles (R-JUNTA=presidente,
      R-COORDINADOR=secretario) y audit con try/except — validar en
      la revisión de aceptación; integración acto administrativo de
      governance quedó como simplificación documentada.
- Nota: `.gitignore` `treasury/` sin anclar ignoraba `apps/treasury/`
  — anclado en `b474232` (mismo bug que legalization, `21fac83`).

## Etapa 4 — Aceptación MVP

- [x] Suite completa verde (419✓/8⏭/0✗/0⚠, 22s) + `makemigrations
      --check` limpio + `manage.py check` limpio.
- [x] Lint: ruff auto-fix (1.440) expuso y reparó 2 NameErrors
      latentes (`add5957`, `f647045`); 35 ítems aceptados como deuda
      documentada. black/isort no instalados en host.
- [x] Walkthrough e2e documentado + roadmap/CHANGES al día
      (`07453e1`) + `docs/mvp-acceptance.md`.
- [ ] **GATES DEL USUARIO**: push con PRs encadenados por commit y
      revisión nativa por slice (RDD ON — global). Detalles de
      corte en este archivo, Etapas 1-3.

## Post-MVP (aprobado por el usuario: "mergea y continua")

- **MVP ENTREGADO**: PR #8 mergeado (`bc86058`), master sincronizado,
  CI verde (pre-commit pineado: el CI destapó un bug real — el HTML
  `AuditEventDetailView` pisaba al DRF y la ruta API `events/<id>`
  servía sin `IsAuditViewer`; renombrado).
- [x] CHG-304 terminación/sanciones (CAP-015/016): serializers +
      router cableado (`/api/condonation/` — estaba inalcanzable),
      auditoría CAP-022 en todos los servicios (sin try/except), 32
      tests (IPC verificado a mano, ventana 30 días Art. 17). PR #10
      mergeado (`9f0b2de`).
- [x] Higiene de media: 10 `comprobante_*.pdf` de tests trackeados en
      el repo → removidos; `MEDIA_ROOT` de tests a tmp (`2c9a0db`).
- [x] CHG-401 seguimiento académico (CAP-011): serializers + router
      cableado (`/api/academic-tracking/`), **bug real corregido**:
      `CONSECUTIVE_LOW_SEMESTRES_TRIGGER` sin definir (NameError latente
      bajo `# noqa: F821` — la suspensión automática del Art. 16 nunca
      pudo ejecutarse), auditoría CAP-022, 20 tests. PR #12 mergeado
      (`b5f0384`).
- [x] Higiene de media definitiva: 0 PDFs trackeados (comprobante.pdf
      sin sufijo + test_doc.pdf removidos en `391bb5c`).
- [x] CHG-207 pendings cerrados (PR #14, `fdf3976`): template
      acto_pdf.html creado (el PDF crasheaba: template + fallback
      inexistentes), bug ContentFile en guardar_pdf_acto, gating del
      portal público verificado con tests (solo PUBLICADO, sin PII),
      e2e del flujo de actos.
- [x] Matriz de roles fina + unificación de códigos fantasma (PR #16,
      `713319b`): seed R-COORD/R-TESOR vs código con R-COORDINADOR
      (13×) / R-TESORERO — nunca matcheaban; unificados a
      R-COORD/R-TESOR/R-SECEDU; R-REVISOR y R-COMITE sembrados;
      matriz fina en condonation y academic + ownership en
      submit_justification; 8 tests.
- [x] Infraestructura de despliegue (PR #18, `4ef4672`): Dockerfile
      producción con GTK libs (WeasyPrint no podía renderizar nada en
      la imagen), conftest multi-DB (respeta DATABASE_URL).
- [x] **Opción A ejecutada — bloqueo de despliegue RESUELTO** (PR #20,
      `47bef60`): migraciones regeneradas UUID-nativas (12 apps, 1
      0001_initial por app + seed OFIJUR), dev DB recreada, backfills y
      sus 34 tests muertos eliminados. La suite corre contra PostgreSQL:
      **454✓/4⏭ en PG / 450✓/8⏭ en sqlite**.
- [x] **ci.yml activo para master**: el job Test (Postgres 16 + Redis +
      GTK) corrió por primera vez — PR #20 Test pass 1m28s. Dependency
      phantoms declarados (crispy-forms, django-filter, Django<6 pin).
- [x] **Bug real — cadena de auditoría se forkea bajo concurrencia**
      (atrappado por test_concurrency en PG real): pg_advisory_xact_lock
      compuesto con row lock. **Bug real — auditoría de treasury
      perdida**: actions > 20 chars + try/except silencioso; widened y
      fail-closed (criterio unificado).
- [x] CHG-501 sesiones de Junta y CT (CAP-017) — PR #22 mergeado
      (`fbc1e66`): propuesta aprobada (issue #21), modelos
      Sesion/MiembroSesion/Punto/Voto/ActaSesion, servicios (convocatoria
      5/2 días hábiles, quórum mitad+1, votación con exenciones y
      exclusiones, acta PDF+SHA-256+firmas ElectronicSigner), API
      `/api/sessions/` con matriz de roles y ownership de voto,
      36 tests. Auditoría CAP-022 fail-closed.
- [ ] Restante post-MVP: Fases 4-5 (reporting/transparencia —
- [x] CHG-502 conflictos de interés (CAP-018) — PR #24 mergeado
      (`51de9b3`): declaración formal por punto (Ley 1952/2019),
      impedimento resuelto por mayoría mitad+1 de presentes habilitados,
      voto excluido cuando se aprueba, API self-service, auditoría,
      15 tests. Bug de integración corregido: el chequeo COI estaba
      anidado bajo can_vote() y no disparaba para miembros elegibles.
- [ ] Restante post-MVP: Fases 4-5 (reporting/
- [ ] Restante post-MVP: Fases 4-5 (gobernanza/sesiones, reporting/
      transparencia — apps removidas por CHG-806), runbooks/DRP
      (INF-011/012/015), unificar criterio de auditoría try/except vs
      fail-closed.

## Riesgos

- Suite con módulo roto desde siempre: los tests de migraciones de
  `claims` nunca corrieron (collection error silencioso).
- Conciliación de checkboxes requiere evidencia por tarea; si algo no
  está implementado se deja pendiente y se reporta.
- El WIP de e-signature no está commiteado: riesgo de pérdida hasta la
  Etapa 0/1.
