# Design — CHG-202 Interfaz HTML para Wizard FUI

## Arquitectura

```
/applications/
├── views.py          # Vistas Django (TemplateView, DetailView)
├── urls.py           # URLs con UUID
└── templates/applications/
    ├── list.html
    ├── detail.html
    ├── wizard.html
    └── partials/
        ├── wizard_step_1.html
        ├── wizard_step_2.html
        ├── wizard_step_3.html
        ├── wizard_step_4.html
        └── wizard_step_5.html
```

## Decisiones de Diseño

### 1. UUID en URLs

- **Por qué**: Ocultar IDs secuenciales previene enumeration attacks
- **Cómo**: Usar `uuid4` generado automáticamente en el modelo
- **Trade-off**: URLs más largas pero más seguras

### 2. Wizard con HTMX

- **Por qué**: Experiencia fluida sin full page reload
- **Cómo**: Partials para cada paso + htmx boost
- **Fallback**: Si JS falla, el formulario funciona con POST normal

### 3. Campos JSON para draft

- **Por qué**: Flexibility para guardar progreso parcial
- **Cómo**: `datos_personales`, `info_academica`, `info_socioeconomica` como JSONField

## Patrones a Seguir

- Usar `LoginRequiredMixin` en todas las vistas
- Usar `get_object_or_404(Application, uuid=uuid, usuario=request.user)`
- Persistir drafts via servicios existentes (`wizard_service.py`)
- Reutilizar validaciones de la API REST

## Dependencias

- `apps/applications/services/wizard_service.py` — `save_draft()`, `submit()`
- `apps/applications/services/radicado_service.py` — `generar_radicado()`
- Templates base existentes en `templates/base.html`
- HTMX ya configurado en el proyecto

## Externo

- S3/MinIO para almacenamiento de anexos (ya configurado)
