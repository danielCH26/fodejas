# CHG-202-applicator-fui — Wizard FUI Digital + Anexos + Radicado (CAP-003)

## Contexto

Con `CHG-201-convocatory-engine` vigente, "Reconocimiento a la
Excelencia 2026-1" (`project.md` §12) puede entrar a
`EN_INSCRIPCION`, pero el **aspirante no tiene cómo radicar FUI**:
el flujo `§10.2` (pasos 2–5) está sin implementar. Sin esto,
**CAP-003 P0 bloquea CAP-004/005**. CHG-105 delega aquí la captura
de consentimiento expreso dentro del FUI.

## Capacidades y Reglas

- **CAP-003 P0** (`project.md` §8, §10.2, §12.3).
- §11 plazos `Decreto 0372/2025 Art. 16`; §13.2 consentimiento Ley
  1581/2012 (CHG-105).
- §6.1 sin PII en fixtures/logs; §6.2 sin integraciones externas.

## Cambios Propuestos

### 1. Modelos (`apps/applications/models.py`)

- `Application(aspirante, convocatoria, radicado_unico UNIQUE,
  estado, datos_personales JSONB, info_academica JSONB,
  info_socioeconomica JSONB, declaracion BOOL, fecha_radicacion)`.
  `estado` ∈ {`borrador`,`radicada`}.
- `Anexo(application, tipo, archivo, sha256, mime, size_bytes,
  uploaded_at)`. Storage S3-compatible (MinIO dev).
- `RadicadoSecuencial(convocatoria, year, last_seq)` →
  `FODEJAS-{year}-{seq:05d}`.

### 2. Servicios (`apps/applications/services/`)

- `wizard_service.py`: `save_draft()`, `submit()` — único punto de
  transición `borrador→radicada`. Valida: convocatoria en
  `EN_INSCRIPCION` (CAP-002), anexos obligatorios completos,
  `Consentimiento` CHG-105 vigente, unicidad (aspirante único
  por convocatoria).
- `radicado_service.py`: atómico con `select_for_update()` sobre
  `RadicadoSecuencial`.
- `pdf_service.py`: WeasyPrint + plantilla con datos y anexos;
  SHA-256 archivado en `Application`.

### 3. Wizard UI (HTMX)

Pasos: (1) datos personales, (2) académica/excelencia,
(3) socioeconómica, (4) anexos, (5) declaración + consentimiento +
radicación. `save_draft()` por paso.

### 4. API + Admin

`POST /api/applications/{id}/save_draft/`, `POST .../submit/`,
`GET /api/convocatorias/{id}/applications/mine/`. Permisos:
aspirante dueño o R-COORD/R-ADMIN. Admin read-only; acciones
delegan al servicio.

## Criterios de Aceptación

- [ ] Radicado `FODEJAS-2026-00001` generado en radicación real.
- [ ] Wizard guarda borrador sin requerir consentimiento.
- [ ] `submit()` rechaza si convocatoria NO está en `EN_INSCRIPCION`.
- [ ] `submit()` rechaza sin anexos obligatorios o sin `Consentimiento`.
- [ ] PDF generado, SHA-256 almacenado, descargable.
- [ ] `AuditEvent` (CAP-022) en cada transición + radicación.

## Pruebas

- Unit: generador radicado (formato, unicidad, secuencia).
- Integración: ciclo completo con convocatoria `en_inscripcion`,
  anexos obligatorios y consentimiento → radicada + PDF + auditoría.
- Negativos: convocatoria en `borrador`/`publicada` → 400;
  doble submit → 409; anexos faltantes → 422.

## Affected Areas

| Área | Impacto |
| --- | --- |
| `apps/applications/models.py` | Nuevo |
| `apps/applications/services/{wizard,radicado,pdf}_service.py` | Nuevo |
| `apps/applications/views.py` + `urls.py` | Nuevo (HTMX wizard) |
| `apps/applications/admin.py` | Nuevo (read-only + acciones) |
| `apps/applications/tests/` | Nuevo (unit + integración) |
| `apps/audit/signals.py` | Modificado (AUDIT_MODELS) |

## Riesgos y Rollback

| Riesgo | Mitigación |
| --- | --- |
| Concurrencia radicado | `select_for_update()` en `RadicadoSecuencial` |
| Storage lleno | `size_bytes` ≤ 10 MB, mime whitelist |
| PII en logs | helper `apps/core/logging.py` |

**Rollback**: migraciones `applications.0001/0002` reversibles;
borradores y radicadas se conservan read-only si se revierte
el deploy.
