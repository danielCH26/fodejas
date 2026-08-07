# Design — CHG-203 Interfaz para Validación de Requisitos

## Arquitectura

```
/applications/
├── models.py              # RequisitoValidacion
├── views.py              # Vistas de revisión
├── urls.py               # URLs con UUID
└── templates/applications/
    └── review/
        ├── list.html     # Lista de solicitudes
        ├── detail.html  # Checklist de requisitos
        └── partials/
            └── requisito_item.html
```

## Decisiones de Diseño

### 1. Modelo RequisitoValidacion

- **Por qué**: Necesidad de tracking por requisito individual
- **Cómo**: Relación 1:N con Solicitud
- **Trade-off**: Más complejidad pero mejor trazabilidad

### 2. Checklist Dinámico

- **Por qué**: Los requisitos varían por convocatoria
- **Cómo**: Leer de `ConfiguracionConvocatoria.requisitos`
- **Beneficio**: Flexibilidad sin código

### 3. Upload de Evidencia por Requisito

- **Por qué**: Cada verificación requiere evidencia documental
- **Cómo**: FileField en cada RequisitoValidacion

## Permisos

| Rol | Acceso |
|-----|--------|
| R-ASPIRANTE | Solo sus propias solicitudes (ver) |
| R-REVISOR | Todas las solicitudes en revisión |
| R-ADMIN | Todas las solicitudes |

## Dependencias

- CHG-202 (applicator-fui-html) — modelo Solicitud con UUID
- CHG-106 (notifications) — para notificar al aspirante
- Configuración de requisitos en Convocation model

## Externo

- S3/MinIO para almacenamiento de evidencias
