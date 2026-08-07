# CHG-205 — Interfaz HTML para Reclamaciones (1ª Instancia)

## Contexto

Después de publicados los resultados preliminares del scoring (CHG-204), los aspirantes insatisffechos pueden presentar **reclamaciones** ante la **Junta Directiva** del FODEJAS en 1ª instancia.

Este cambio implementa la interfaz HTML para que los aspirantes presenten reclamaciones y la Junta las gestione.

## Capacidades afectadas

- **CAP-006** — Reclamaciones (1ª instancia ante la Junta)
- **CAP-022** — Bitácora de auditoría (ya implementado)

## Reglas de negocio afectadas

- `project.md §10.3` — Flujo de Reclamación / Apelación
- `project.md §11.6` — No hay normativa específica para plazo de reclamaciones; se usará **15 días hábiles** desde publicación de resultados preliminares (típico en admin público)
- `project.md §13.4` — Cumplimiento CPACA

## Cambios propuestos

### 1. Modelo Reclamacion

```python
class Reclamacion(models.Model):
    class TipoReclamacion(models.TextChoices):
        PUNTAJE = "puntaje", _("Puntaje incorrecto")
        REQUISITO = "requisito", _("Requisito mal validado")
        OTRO = "otro", _("Otro")

    class Estado(models.TextChoices):
        PRESENTADA = "presentada", _("Presentada")
        EN_REVISION = "en_revision", _("En revisión")
        RESUELTA = "resuelta", _("Resuelta")
        RECHAZADA = "rechazada", _("Rechazada")

    uuid = models.UUIDField(unique=True, editable=False)
    solicitud = models.ForeignKey("applications.Solicitud", on_delete=models.CASCADE)
    tipo = models.CharField(TipoReclamacion.choices)
    descripcion = models.TextField()
    evidencia = models.FileField(upload_to="reclamaciones/", blank=True)
    estado = models.CharField(Estado.choices, default=Estado.PRESENTADA)
    respuesta = models.TextField(blank=True)
    resuelto_por = models.ForeignKey(User, null=True, blank=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 2. Modelo ReclamacionHistorial

Para auditoría de cambios de estado.

### 3. Vistas HTML

| Vista | URL | Permiso |
|-------|-----|---------|
| ReclamacionCreateView | POST /claims/crear/<uuid:solicitud>/ | R-ASPIRANTE (owner) |
| ReclamacionListView | /claims/ | R-ASPIRANTE (mis reclamaciones) |
| ReclamacionDetailView | /claims/<uuid:pk>/ | R-ASPIRANTE (owner) o R-JUNTA |
| ReclamacionUpdateView | /claims/<uuid:pk>/editar/ | Dueño si estado PRESENTADA |
| ReclamacionResolveView | /claims/<uuid:pk>/resolver/ | R-JUNTA |
| ReclamacionListAdminView | /claims/admin/ | R-JUNTA, R-ADMIN |

### 4. Flujo

1. Aspirante recibe notificación de resultados preliminares
2. Aspirante presenta reclamación dentro del plazo (15 días hábiles)
3. Sistema registra reclamación y envía notificación a Coordinación
4. Junta revisa, solicita info adicional si es necesario
5. Junta resuelve (acepta/rechaza) con respuesta fundamentada
6. Aspirante notificado del resultado

### 5. Permisos

- **R-ASPIRANTE**: crear reclamaciones, ver las propias
- **R-JUNTA**: ver todas, resolver reclamaciones
- **R-ADMIN**: superuser access

### 6. Notificaciones

- Al presentar: notificación a Coordinación Técnica
- Al resolver: notificación al aspirante

## Criterios de aceptación

- [ ] Modelo Reclamacion con UUID en URLs
- [ ] Vista para crear reclamación desde resultados preliminares
- [ ] Lista de reclamaciones del usuario
- [ ] Panel de administración para Junta (listado + detalle)
- [ ] Resolución con respuesta fundamentada
- [ ] Historial de cambios de estado
- [ ] Notificaciones integradas (CAP-019)
- [ ] Auditoría de todas las acciones (CAP-022)

## Pruebas

- Tests unitarios para modelo y vistas
- Tests de flujo: presentar -> resolver
- Verificar permisos por rol
- Verificar UUID en URLs

## Riesgos

- **Plazo**: Si no hay normativa específica,documentar el plazo usado
- **Dependencia**: Requiere CHG-204 (scoring) publicado
- **Fuera de alcance**: 2ª instancia (apelaciones) = CHG-206
