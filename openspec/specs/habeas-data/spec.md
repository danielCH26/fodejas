# Habeas Data — Spec

## Purpose

Consentimientos y derechos ARCO exigidos por **Ley 1581/2012** y
**Decreto 1377/2013**. Cubre **CAP-025** (`project.md` §5.5,
`roadmap.md` §5.1). Bloquea CAP-002..CAP-030 si falta.

## ADDED Requirements

### Requirement: Consentimiento Versionado

El sistema SHALL registrar cada otorgamiento con **texto íntegro
firmado** y **hash SHA-256** inmutable por versión. Cambios de
política SHALL crear nueva versión; la previa SHALL marcarse
`revocado_en` sin borrarse.

#### Scenario: Otorgamiento FUI

- GIVEN titular autenticado en FUI con versión `v3`
- WHEN confirma y se persiste
- THEN `Consentimiento` activo con `hash_texto = sha256(v3)`,
  `revocado_en IS NULL`

#### Scenario: Nueva versión revoca la anterior

- GIVEN `Consentimiento` activo `v3`
- WHEN titular acepta `v4`
- THEN `v3.revocado_en = now()` y `v4` queda activa

#### Scenario: Texto alterado post-firma

- GIVEN `Consentimiento` con `hash_texto` registrado
- WHEN un proceso modifica `version_texto`
- THEN falla con `HashMismatch` y `audit` emite `consent.tamper`

### Requirement: SolicitudHabeasData (ARCO)

El sistema SHALL permitir al titular autenticado ejercer cada derecho
ARCO (**Art. 14 Ley 1581/2012**): `consulta`, `rectificacion`,
`actualizacion`, `supresion`. Cada solicitud SHALL tener un solo
`tipo` y referenciar al titular autenticado.

#### Scenario: Radicación de consulta

- GIVEN titular autenticado con descripción del dato
- WHEN POST `/api/habeas-data/solicitudes/`
- THEN crea `estado=radicada`, `fecha_limite=now()+30h`,
  notifica (CAP-019) y emite `habeas.created`

#### Scenario: Solicitud sin autenticación

- GIVEN request sin token JWT
- WHEN POST `/api/habeas-data/solicitudes/`
- THEN retorna `401 Unauthorized`

#### Scenario: Solicitud a nombre de tercero

- GIVEN titular autenticado intenta radicar para otro `user_id`
- WHEN se persiste
- THEN retorna `403` y `audit` emite `habeas.unauthorized`

### Requirement: Plazo de 30 Días Hábiles

El sistema SHALL calcular `fecha_limite` sumando **30 días hábiles**
(sábados, domingos y festivos — Ley Emiliani 51/1983, Decreto
1175/2011) desde `fecha_radicacion`. `vencida` SHALL activarse cuando
`now() > fecha_limite` y `estado ∈ {radicada, en_tramite}`. Celery
SHALL alertar a R-ADMIN/R-COORD en el **día 25** hábil.

#### Scenario: Cálculo correcto

- GIVEN radicación un martes con festivo el jueves
- WHEN se calcula `fecha_limite`
- THEN corresponde al trigésimo día hábil siguiente

#### Scenario: Transición a vencida

- GIVEN solicitud `en_tramite` con `fecha_limite` superada
- WHEN corre Celery `habeas_expiry_check`
- THEN `estado=vencida` y notifica responsable + titular

#### Scenario: Alerta día 25

- GIVEN solicitud radicada hace 24 días hábiles
- WHEN corre el beat diario
- THEN R-ADMIN/R-COORD reciben `habeas.expiring_soon`

### Requirement: Transiciones y Rechazo

`estado` SHALL transicionar:
`radicada → en_tramite → {resuelta | rechazada}`; `vencida` terminal.
Solo R-ADMIN/R-COORD SHALL transicionar; SHALL exigir `respuesta` no
vacía para `resuelta` y `motivo` para `rechazada`. Cada transición
SHALL notificar (CAP-019) y registrar en `audit` (CAP-022) con PII
enmascarada vía `apps/core/logging.py`.

#### Scenario: Resolución con respuesta

- GIVEN solicitud `en_tramite`
- WHEN R-COORD `{estado: resuelta, respuesta: "…"}`
- THEN `estado=resuelta`, titular notificado, `audit`
  emite `habeas.resolved`

#### Scenario: Resolución sin respuesta

- GIVEN R-COORD intenta `{estado: resuelta}` sin `respuesta`
- WHEN se valida
- THEN retorna `400 "La respuesta es obligatoria"`

#### Scenario: Rechazo con motivo

- GIVEN solicitud fuera del alcance del Responsable
- WHEN R-COORD `{estado: rechazada, motivo: "no aplica"}`
- THEN `estado=rechazada` y titular notificado con fundamento

### Requirement: Supresión con Soft-Delete

Cuando una solicitud ARCO `supresion` pase a `resuelta`, los datos del
titular SHALL marcarse con `suprimido_en=now()` para preservar la
bitácora durante **20 años** (`project.md` §5.5). SHALL NOT ejecutarse
con **actos firmes** (CAP-008); SHALL responderse con `rechazada` y
razón normativa.

#### Scenario: Supresión exitosa

- GIVEN titular sin actos firmes
- WHEN la supresión se resuelve
- THEN datos quedan con `suprimido_en`; `audit` conserva trazabilidad

#### Scenario: Supresión bloqueada por acto firme

- GIVEN titular con `Resolucion` perfeccionada
- WHEN R-COORD intenta resolver la supresión
- THEN retorna `409 "Supresión bloqueada por acto firme"`

### Requirement: Admin Django para R-ADMIN / R-COORD

`/admin/accounts/solicitudhabeasdata/` y
`/admin/accounts/consentimiento/` SHALL restringirse a R-ADMIN/R-COORD
(CAP-001). Lista SHALL filtrar por `estado`, `tipo`, fechas. Vista
individual SHALL permitir `responder`, `rechazar` con motivo y
adjuntar **evidencia** en storage S3-compatible.

#### Scenario: Listado filtrable

- GIVEN R-ADMIN en `/admin/accounts/solicitudhabeasdata/`
- WHEN aplica filtro `estado=en_tramite`
- THEN ve solo solicitudes activas con `fecha_limite` resaltada

#### Scenario: Respuesta con evidencia

- GIVEN R-COORD abre solicitud `radicada`
- WHEN `{estado: resuelta, respuesta, evidencia_url}`
- THEN valida REST y `audit` registra responsable

#### Scenario: Usuario sin rol intenta acceder

- GIVEN R-CT en `/admin/accounts/solicitudhabeasdata/`
- WHEN navega al admin
- THEN retorna `403` y `audit` registra `permission_denied`
