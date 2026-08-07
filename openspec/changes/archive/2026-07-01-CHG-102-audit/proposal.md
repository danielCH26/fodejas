# CHG-102-audit — Bitácora de Auditoría Inmutable (CAP-022)

## Contexto

El proyecto requiere una bitácora de auditoría que registre todas las acciones sobre cualquier modelo de forma inmutable, con encadenamiento de hashes (hash chain) para garantizar integridad.

Según `project.md` §13.3:
- Tabla append-only con encadenamiento de hashes
- Captura: timestamp UTC, actor, acción, entidad, id, antes/después (resumen), IP, user-agent, módulo
- Retención: 20 años

Según `AGENTS.md` §6:
- La bitácora es append-only con hash chain
- Se inserta desde servicio/contexto, nunca desde la vista

## Capacidades Afectadas

- **CAP-022** — Bitácora de Auditoría (inmutable)

## Reglas de Negocio Afectadas

- `project.md` §13.3 — Bitácora de Auditoría
- `project.md` §13.5 — Roles y Segregación de Funciones (la auditoría es parte del control)

## Cambios Propuestos

### 1. Modelo AuditEvent

Tabla `audit_auditevent` con campos:
- `id`: UUID primary key
- `timestamp`: DateTime UTC (indexado)
- `actor`: FK a User (nullable para acciones system)
- `action`: Char (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, ACCESS)
- `entity`: Char (nombre del modelo, ej: "Convocatoria", "User")
- `entity_id`: UUID de la entidad afectada
- `changes`: JSON con {before, after} (solo para UPDATE)
- `ip_address`: GenericIPAddressField
- `user_agent`: Text
- `module`: Char (app label)
- `previous_hash`: Char(64) — hash SHA-256 del registro anterior
- `current_hash`: Char(64) — hash SHA-256 de este registro (incluye previous_hash)
- `is_valid`: Boolean — indica si el hash es válido (para verificación)

### 2. Servicio de Auditoría

- `apps/audit/services.py`: función `log_audit_event()` que:
  - Calcula hash incluyendo el hash anterior
  - Valida integridad de la cadena
  - Inserta el evento
  - Usa señales Django (post_save, post_delete) para automático

### 3. Señales de Auditoría

- Conectar a todos los modelos de las apps principales:
  - accounts: CustomUser, Role, Permission
  - convocatories: Convocatoria, ConvocatoriaRequisito
  - applications: Solicitud
  - scoring: Scoring
  - legalization: Legalizacion
  - treasury: Desembolso

### 4. API de Consulta

- `GET /api/audit/events/` — listar eventos con filtros
- `GET /api/audit/events/{id}/` — detalle de un evento
- `GET /api/audit/verify/` — verificar integridad de la cadena

## Criterios de Aceptación

- [ ] El modelo AuditEvent persiste con todos los campos definidos
- [ ] El hash chain funciona: cada registro incluye el hash del anterior
- [ ] Las señales registran automáticamente acciones en modelos principales
- [ ] La API permite consultar eventos con filtros (actor, entidad, fecha)
- [ ] La verificación de cadena retorna válido/inválido
- [ ] Los tests verifican hash chain y signals

## Pruebas

- Unit tests para hash calculation
- Integration tests para signals
- API tests para endpoints de consulta

## Riesgos

- Performance: crear índices apropiados para queries frecuentes
- Storage: 20 años de retention requiere planificación de archival

## Outside Scope

- Exportación a entes de control (CAP-028)
- Auditoría en tiempo real (streaming)
- Alertas basadas en auditoría
