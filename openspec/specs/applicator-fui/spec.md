# Spec for applicator-fui

## Purpose

Wizard FUI digital, anexos, radicado y PDF para **CAP-003 P0**
(`project.md` §8, §10.2 pasos 2–5, §12.3). Habilita CAP-004/005.
App: `apps/applications/`. Dependencias: CAP-001 auth, CAP-002
`en_inscripcion`, CHG-105 `Consentimiento`.

## ADDED Requirements

### Requirement: Solicitud (Application) Model

`Application(aspirante FK, convocatoria FK, radicado_unico
UNIQUE, estado ∈ {borrador, radicada}, datos_personales JSONB,
info_academica JSONB, info_socioeconomica JSONB, declaracion
BOOL, fecha_radicacion NULL, pdf_sha256 NULL)`.
`radicado_unico` SHALL formato `FODEJAS-YYYY-NNNNN`. UNIQUE
`(aspirante, convocatoria)`: a lo sumo una solicitud.
SHALL asignarse **solo** al transicionar a `radicada`.

#### Scenario: Primer borrador

- GIVEN aspirante autenticado, convocatoria `en_inscripcion`
  sin solicitud previa
- WHEN abre el wizard
- THEN `Application.borrador` con `radicado_unico IS NULL`;
  `audit application.created`

#### Scenario: Doble intento devuelve único borrador

- GIVEN ya existe `Application(borrador)` para
  `(aspirante, convocatoria)`
- WHEN intenta crear otra
- THEN retorna la misma instancia; sin duplicado

### Requirement: Radicado — Secuencia Atómica

`services/radicado_service.py::generar_radicado(convocatoria,
year)` SHALL asignar `FODEJAS-{year}-{seq:05d}` en
`transaction.atomic()` con `select_for_update()` sobre
`RadicadoSecuencial(convocatoria, year)`. Concurrencia SHALL
resolverse sin huecos/duplicados (UNIQUE como segunda línea).

#### Scenario: Primera radicación

- GIVEN `RadicadoSecuencial(2026)` ausente
- WHEN `submit()` crea y asigna
- THEN `radicado="FODEJAS-2026-00001"`, `last_seq=1`

#### Scenario: Concurrencia sin duplicados

- GIVEN 5 requests paralelos con `seq=42`
- WHEN se procesa con `select_for_update()`
- THEN consecutivos `43..47`, sin `IntegrityError`

### Requirement: FUI Wizard — Multi-Step Draft

5 pasos: (1) personales, (2) académica/excelencia, (3)
socioeconómica, (4) anexos, (5) declaración+consentimiento+
radicación. `save_draft(step, payload)` SHALL persistir el JSON
manteniendo `borrador` **sin** exigir consentimiento, anexos ni
validaciones cerradas.

#### Scenario: Avance progresivo

- GIVEN borrador en paso 1
- WHEN completa pasos 2–4 vía HTMX
- THEN cada `save_draft()` persiste JSON, permanece `borrador`

#### Scenario: Re-edición no destruye avance

- GIVEN borrador con pasos 1–3 completos
- WHEN edita y guarda paso 1
- THEN paso 1 actualizado, 2–3 intactos

### Requirement: Anexo — Upload + Validación

`Anexo(application, tipo, archivo, sha256, mime, size_bytes,
uploaded_at)` en S3-compatible. Tipos requeridos por
`ConfiguracionConvocatoria.anexos_obligatorios` (CAP-024).
`size_bytes` SHALL ≤ 10 MB; `mime` ∈ whitelist
(`application/pdf`, `image/jpeg`, `image/png`).

#### Scenario: Subida válida

- GIVEN paso 4 con `anexos_obligatorios=["documento_identidad"]`
- WHEN sube PDF 2 MB
- THEN `Anexo` con `sha256`, descargable

#### Scenario: Tamaño excedido / mime prohibido

- WHEN sube 12 MB o `.exe`
- THEN `422`; sin persistir

### Requirement: Submit — Predicados Cerrados

`services/wizard_service.py::submit(application, *,
consentimiento, actor)` SHALL ser único punto `borrador→
radicada`. Exigir: convocatoria `en_inscripcion` (CAP-002/
CHG-201), `Consentimiento` vigente (CHG-105), todos
`anexos_obligatorios` presentes, `declaracion=True`. Éxito SHALL
generar radicado, `pdf_service`, `audit
application.radicated {radicado, pdf_sha256}` y `Notification
application.submitted`.

#### Scenario: Radicación exitosa

- GIVEN borrador válido, convocatoria `en_inscripcion`,
  consentimiento, anexos completos, `declaracion=True`
- WHEN `submit()`
- THEN `radicada`, `radicado_unico`, `fecha_radicacion=now()`,
  PDF, `audit`, `Notification`

#### Scenario: Convocatoria cerrada

- GIVEN convocatoria `publicada`/`en_verificacion`/`definitiva`
- WHEN `submit()`
- THEN `400 "Convocatoria no admite inscripciones (CAP-002)"`

#### Scenario: Anexos faltantes / sin consentimiento

- WHEN faltan anexos o `Consentimiento` revocado/ausente
- THEN `422` con detalle / `412 "Consentimiento Ley 1581/2012
  vigente requerido"`; sin transición

#### Scenario: Doble submit

- GIVEN ya `radicada`
- WHEN segundo `submit()`
- THEN `409`; sin nuevos `audit`/`Notification`

### Requirement: PDF Generation — WeasyPrint + SHA-256

`services/pdf_service.py::generar_pdf(application)` SHALL
renderizar plantilla WeasyPrint, calcular `SHA-256` y persistir
en `Application.pdf_sha256` dentro del mismo
`transaction.atomic()` que `submit()`. Post-radicación SHALL
ser inalterable: regenerar SHALL fallar
`ValidationError("PDF inmutable")` salvo reissue audit-logged
con `motivo` (CHG-029).

#### Scenario: Generación inicial

- GIVEN application recién radicada sin pdf
- WHEN `generar_pdf()`
- THEN archivo escrito, `pdf_sha256` populado, descargable vía
  endpoint autenticado

#### Scenario: Regeneración denegada

- GIVEN radicada con `pdf_sha256` previo
- WHEN regenera sin `motivo`
- THEN `ValidationError`; `audit pdf.regenerate_denied`

### Requirement: API + RBAC (CAP-001)

| Método | Path                                              | Permiso        |
| ------ | ------------------------------------------------- | -------------- |
| POST   | `/api/applications/{id}/save_draft/`              | dueño o R-COORD|
| POST   | `/api/applications/{id}/submit/`                  | dueño          |
| GET    | `/api/convocatorias/{id}/applications/mine/`      | aspirante      |
| GET    | `/api/applications/{id}/pdf/`                     | dueño/R-COORD/R-ADMIN |

Toda mutación SHALL delegar al servicio. Admin Django
read-only (`AGENTS.md` §6.6).

#### Scenario: Tercero intenta submit

- GIVEN application ajena
- WHEN otro usuario POST `.../submit/`
- THEN `403`; `audit permission_denied`

## Constraints

- Lógica SHALL vivir en `services/` (`AGENTS.md` §6.6).
- `radicado_unico` SHALL asignarse **solo** al transicionar.
- `pdf_sha256` SHALL persistirse en el mismo `atomic()` que
  `submit()` (CAP-022).
- Sin PII en logs/`audit` (`apps/core/logging.py` §6.1).
- Sin integraciones externas (§6.2).
- Plazos CAP-002: `en_inscripcion` durante `submit()`.
- `AUDIT_MODELS` SHALL incluir `Application`, `Anexo`,
  `RadicadoSecuencial`.
