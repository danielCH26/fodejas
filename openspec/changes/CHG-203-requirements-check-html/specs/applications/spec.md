# Spec for CHG-203 — Interfaz HTML para Validación de Requisitos

## Purpose

Interfaz HTML para que la Coordinación Técnica verifique los requisitos mínimos de cada solicitud radicada (CAP-004).

## ADDED Requirements

### Requirement: RequisitoValidacion Model

Nuevo modelo SHALL existir:

```
RequisitoValidacion(
    solicitud FK,
    requisito_code str,  # e.g., "r1_sniees", "r2_sisben"
    estado ∈ {pendiente, verificado, rechazado, subsanar},
    evidencia FileField NULL,
    observaciones text,
    validado_por FK (User),
    fecha_validacion DateTime,
    created_at DateTime,
    updated_at DateTime
)
```

Uniqueness: `(solicitud, requisito_code)` — un validation por requisito.

### Requirement: RequirementReviewListView

- Filtro: solicitudes con `estado = RADICADA` o `estado = EN_VERIFICACION`
- Permiso: usuario con rol R-REVISOR
- Columnas: radicado, convocatoria, aspirante, fecha radicación, progreso verificación

#### Scenario: Revisor ve solicitudes pendientes

- GIVEN revisor autenticado con rol R-REVISOR
- WHEN visita `/applications/revision/`
- THEN ve lista de solicitudes radicadas pendientes de verificación

### Requirement: RequirementReviewDetailView

- Muestra los 7 requisitos configurable desde `ConfiguracionConvocatoria.requisitos`
- Cada requisito tiene: nombre, descripción, checkbox, campo evidencia, observaciones
- Upload de evidencia por cada requisito
- Estados: pendiente → verificado | rechazado | subsanar

#### Scenario: Verificar un requisito

- GIVEN revisor en detalle de solicitud
- WHEN marca requisito como "verificado" y sube evidencia
- THEN `RequisitoValidacion` se crea con estado `verificado`
- AND progreso se actualiza en la UI

#### Scenario: Solicitar subsanación

- GIVEN requisito en estado "subsanar"
- WHEN revisor guarda con observaciones
- THEN estado de Solicitud cambia a `borrador` (para corrección)
- AND aspirante recibe notificación

### Requirement: Aprobación/Rechazo Final

- Botón "Aprobar Todos" — solo activa si todos requisitos están verificados
- Botón "Rechazar" — requiere al menos un requisito rechazado
- Al aprobar: Solicitud.estado → `en_verificacion` → `verificada`
- Al rechazar: Solicitud.estado → `rechazada`

#### Scenario: Aprobación completa

- GIVEN todos los requisitos verificados
- WHEN revisor hace click en "Aprobar"
- THEN Solicitud.estado cambia a `verificada`
- AND se registra en auditoría

### Requirement: Historial de Verificaciones

- Cada cambio de estado crea registro de auditoría
- Vista de historial muestra: quién, cuándo, qué cambió

### Requirement: Plantilla de Requisitos

Los requisitos se configuran en `ConfiguracionConvocatoria.requisitos`:

```json
{
  "requisitos": [
    {"code": "r1", "name": "Verificar SNIES", "description": "..."},
    {"code": "r2", "name": "Verificar SISBÉN", "description": "..."},
    ...
  ]
}
```

La UI SHALL leer esta configuración y generar el checklist dinámicamente.

### Requirement: Seguridad

- Solo R-REVISOR puede acceder a vistas de revisión
- UUID en todas las URLs
- Verificar ownership: revisor puede ver cualquier solicitud (no solo las propias)

## MODIFIED Files

- `apps/applications/models.py` — agregar `RequisitoValidacion`
- `apps/applications/views.py` — agregar vistas de revisión
- `apps/applications/urls.py` — agregar URLs
- `templates/applications/review/` — templates

## Acceptance Criteria

- [ ] Modelo RequisitoValidacion existe y funciona
- [ ] Lista de solicitudes en revisión visible para R-REVISOR
- [ ] Checklist de requisitos se genera dinámicamente
- [ ] Upload de evidencia funciona por requisito
- [ ] Estados se actualizan correctamente
- [ ] Botones aprobar/rechazar funcionan
- [ ] Notificaciones se envían al aspirante
- [ ] Historial de cambios visible
- [ ] Todas las URLs usan UUID
- [ ] Permisos correctamente aplicados
