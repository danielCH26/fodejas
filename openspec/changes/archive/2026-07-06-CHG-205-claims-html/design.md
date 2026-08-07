# Design — CHG-205 Interfaz HTML para Reclamaciones

## Arquitectura

### App: `apps/claims/`

```
apps/claims/
├── models.py          # Reclamacion, ReclamacionHistorial
├── views.py           # Vistas HTML (LoginRequiredMixin)
├── urls.py           # Rutas con UUID
├── services/
│   └── claims_service.py  # Lógica de negocio
├── domain/
│   └── transitions.py     # Transiciones de estado
└── templates/claims/
    ├── create.html
    ├── list.html
    ├── detail.html
    └── admin/
        └── list.html
```

## Modelo de Datos

### Reclamacion

| Campo | Tipo | Descripción |
|-------|------|-------------|
| uuid | UUID | Identificador público (URLs) |
| solicitud | FK(Solicitud) | Postulación afectada |
| tipo | Enum | puntaje/requisito/otro |
| descripcion | Text | Motivo de la reclamación |
| evidencia | File | Adjuntos (opcional) |
| estado | Enum | presentada/en_revision/resuelta/rechazada |
| respuesta | Text | Fundamentación de la resolución |
| resuelto_por | FK(User) | Funcionario que resuelve |
| fecha_resolucion | DateTime | Momento de resolución |

### ReclamacionHistorial

| Campo | Tipo |
|-------|------|
| reclamacion | FK(Reclamacion) |
| estado_anterior | Char |
| estado_nuevo | Char |
| observacion | Text |
| actor | FK(User) |
| timestamp | DateTime |

## Permisos

### R-ASPIRANTE
- `claims:create` — Crear reclamación (solo sus solicitudes)
- `claims:list` — Ver sus reclamaciones
- `claims:detail` — Ver detalle de sus reclamaciones

### R-JUNTA
- `claims:admin_list` — Ver todas las reclamaciones
- `claims:resolve` — Resolver reclamaciones
- `claims:request_info` — Solicitar información adicional

## Transiciones de Estado

```
PRESENTADA → EN_REVISION (Junta inicia revisión)
EN_REVISION → RESUELTA (Junta acepta)
EN_REVISION → RECHAZADA (Junta rechaza)
PRESENTADA → RECHAZADA (por vencimiento)
```

## Integraciones

- **CAP-022 (Auditoría)**: Cada transición registra evento
- **CAP-019 (Notificaciones)**: Notificaciones al presentar y resolver
- **CHG-204**: Botón "Presentar Reclamación" desde resultados

## URLs

```
/claims/                          → Lista del usuario
/claims/crear/<uuid:solicitud>/   → Crear reclamación
/claims/<uuid:pk>/                → Detalle
/claims/<uuid:pk>/editar/         → Editar (si PRESENTADA)
/claims/admin/                    → Panel Junta
/claims/admin/<uuid:pk>/          → Revisar resolución
```

## Dependencias

- CHG-202 (Wizard FUI) — Modelo Solicitud con UUID
- CHG-204 (Scoring) — Resultados preliminares
- CHG-106 (Notificaciones) — Notificaciones
- CHG-101/AUDIT (Auditoría) — Bitácora
