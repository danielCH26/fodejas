# Audit Specification — CAP-022

## 1. Purpose

Define an immutable audit log system with hash chain for the FODEJAS platform.

## 2. Scope

All CRUD operations on core domain models must be logged with cryptographic chain integrity.

## 3. Requirements

### 3.1 AuditEvent Model

The system SHALL have an `AuditEvent` model with:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| timestamp | DateTime (UTC) | When the action occurred |
| actor | FK to User | Who performed the action (nullable for system) |
| action | Char | CREATE, UPDATE, DELETE, LOGIN, LOGOUT, ACCESS |
| entity | Char | Model name (e.g., "Convocatoria", "User") |
| entity_id | UUID | ID of the affected entity |
| changes | JSON | {before, after} for UPDATE operations |
| ip_address | GenericIP | Client IP address |
| user_agent | Text | Client user agent |
| module | Char | App label |
| previous_hash | Char(64) | SHA-256 hash of previous record |
| current_hash | Char(64) | SHA-256 hash of this record (includes previous_hash) |
| is_valid | Boolean | Whether the hash chain is valid |

### 3.2 Hash Chain

- Each audit record SHALL contain the SHA-256 hash of the previous record.
- The current hash SHALL be calculated including: timestamp, actor, action, entity, entity_id, changes, previous_hash.
- The chain SHALL be verifiable: `verify_chain()` returns True if all hashes match.

### 3.3 Automatic Logging

- The system SHALL use Django signals to automatically log:
  - post_save: CREATE and UPDATE actions
  - post_delete: DELETE actions
  - User login/logout events

### 3.4 Audit API

The system SHALL provide:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/audit/events/` | GET | List events with filters |
| `/api/audit/events/{id}/` | GET | Event detail |
| `/api/audit/verify/` | GET | Verify chain integrity |

Query parameters for list:
- `actor`: filter by user ID
- `entity`: filter by model name
- `action`: filter by action type
- `start_date`: filter by timestamp
- `end_date`: filter by timestamp

### 3.5 Retention

- Audit records SHALL be retained for 20 years (per project.md §13.3).

## 4. Scenarios

### 4.1 User Creates Convocation

**Given** una convocatoria nueva es creada por un coordinador
**When** se guarda el modelo Convocatoria
**Then** un AuditEvent es creado con:
- action = "CREATE"
- entity = "Convocatoria"
- entity_id = ID de la convocatoria
- changes = {after: {...}}
- previous_hash = hash del último evento
- current_hash = hash calculado

### 4.2 User Updates Application Status

**Given** un miembro del CT cambia el estado de una solicitud
**When** se guarda el modelo Solicitud con nuevo estado
**Then** un AuditEvent es creado con:
- action = "UPDATE"
- entity = "Solicitud"
- entity_id = ID de la solicitud
- changes = {before: {estado: "pendiente"}, after: {estado: "aprobada"}}

### 4.3 Chain Verification

**Given** la cadena de auditoría existe
**When** se llama a `/api/audit/verify/`
**Then** retorna:
- is_valid: true/false
- last_valid_hash: hash del último registro válido
- break_point: ID donde la cadena se rompe (si aplica)

### 4.4 Query by Date Range

**Given** un usuario filtra eventos por fecha
**When** GET `/api/audit/events/?start_date=2026-01-01&end_date=2026-01-31`
**Then** retorna solo eventos en ese rango

### 4.5 Query by Entity

**Given** un usuario quiere ver todas las acciones en una convocatoria
**When** GET `/api/audit/events/?entity=Convocatoria&entity_id=<uuid>`
**Then** retorna todos los eventos para esa entidad específica

## 5. Constraints

- Hash computation MUST use SHA-256.
- Previous hash of first record SHALL be "0" * 64 (64 zeros).
- Audit writes are append-only; no UPDATE or DELETE allowed.
- All audit writes MUST include transaction atomicity.
