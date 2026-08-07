# Design: CHG-202-applicator-fui — Wizard FUI Digital

## Technical Approach

Implement a multi-step FUI (Formulario Único de Inscripción) wizard using HTMX for smooth user experience without page reloads. The application process is split into logical steps that can be saved as drafts.

## Architecture Decisions

| # | Decision | Choice | Alternatives | Rationale |
|---|----------|--------|--------------|----------|
| 1 | Wizard frontend | HTMX | React/Vue SPA | AGENTS.md §2: no SPA in first iteration |
| 2 | File storage | S3-compatible (MinIO) | Local filesystem | Matches project storage strategy |
| 3 | PDF generation | WeasyPrint | ReportLab | Already in project stack |
| 4 | Radicado format | FODEJAS-YYYY-NNNNN | UUID | Human-readable, sortable |
| 5 | Draft storage | JSONField on Solicitud | Separate table | Simpler, single query |

## Data Flow

```
User starts FUI
       │
       ▼
Step 1: Datos Personales ──save draft──► Solicitud (estado=borrador)
       │
       ▼
Step 2: Información Académica ──save draft──► Solicitud.datosAcademicos JSON
       │
       ▼
Step 3: Información Socioeconómica ──save draft──► Solicitud.datosSocioeconomicos JSON
       │
       ▼
Step 4: Carga de Anexos ──upload──► Anexo table (sha256 stored)
       │
       ▼
Step 5: Revisión y Firma ──submit──► Validate all → Generate radicado → Generate PDF
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `apps/applications/models.py` | Create | Solicitud, Anexo models |
| `apps/applications/domain/__init__.py` | Create | Package init |
| `apps/applications/domain/validators.py` | Create | FUI validation logic |
| `apps/applications/services/__init__.py` | Create | Package init |
| `apps/applications/services/radicado_service.py` | Create | Radicado generation |
| `apps/applications/services/pdf_service.py` | Create | PDF generation |
| `apps/applications/selectors.py` | Create | Application selectors |
| `apps/applications/api/serializers.py` | Create | API serializers |
| `apps/applications/api/views.py` | Create | API views |
| `apps/applications/api/urls.py` | Create | API URLs |
| `apps/applications/admin.py` | Create | Admin configuration |
| `apps/applications/apps.py` | Create | App config |
| `apps/applications/urls.py` | Create | URL config |
| `templates/applications/` | Create | HTML templates |

## Models

### Solicitud
- `radicado`: CharField (unique, FODEJAS-YYYY-NNNNN)
- `convocatoria`: FK to Convocatory
- `aspirante`: FK to User
- `estado`: TextChoices (borrador, completa, radicada, verificada, rechazada)
- `datos_personales`: JSONField
- `datos_academicos`: JSONField
- `datos_socioeconomicos`: JSONField
- `pdf_generado`: FileField
- `pdf_sha256`: CharField
- `current_step`: IntegerField (1-5)

### Anexo
- `solicitud`: FK to Solicitud
- `tipo_anexo`: CharField (certificado_notas, documento_identidad, etc.)
- `archivo`: FileField
- `sha256`: CharField
- `validated`: BooleanField

## API Endpoints

| Method | Path | Description |
|--------|-------|-------------|
| GET | /api/solicitudes/ | List user's solicitudes |
| POST | /api/solicitudes/ | Create new draft |
| GET | /api/solicitudes/{id}/ | Get solicitud details |
| PATCH | /api/solicitudes/{id}/ | Update draft |
| POST | /api/solicitudes/{id}/submit/ | Submit completed FUI |
| POST | /api/solicitudes/{id}/anexos/ | Upload anexo |
| GET | /api/solicitudes/{id}/pdf/ | Download generated PDF |

## Testing Strategy

| Layer | What | Approach |
|-------|------|---------|
| Unit | Radicado generation | Mock-free test with counter |
| Unit | Validation logic | Table-driven tests |
| Integration | Wizard flow | Selenium or API tests |
| Integration | File upload | Test S3/MinIO |
| Integration | PDF generation | WeasyPrint render test |

## Open Questions

- [ ] Should anexo validation be automatic or manual? (Deferred)
- [ ] How long to keep drafts? (30 days suggested)
