# Spec for CHG-205 — Interfaz HTML para Reclamaciones

## ADDED

### Modelo Reclamacion

```python
class Reclamacion(models.Model):
    """Reclamación en 1ª instancia ante la Junta Directiva."""

    class TipoReclamacion(models.TextChoices):
        PUNTAJE = "puntaje", _("Puntaje incorrecto")
        REQUISITO = "requisito", _("Requisito mal validado")
        OTRO = "otro", _("Otro")

    class Estado(models.TextChoices):
        PRESENTADA = "presentada", _("Presentada")
        EN_REVISION = "en_revision", _("En revisión")
        RESUELTA = "resuelta", _("Resuelta")
        RECHAZADA = "rechazada", _("Rechazada")

    # UUID para URLs públicas
    uuid = models.UUIDField(
        unique=True,
        editable=False,
        db_index=True,
    )

    # Relación con la postulación
    solicitud = models.ForeignKey(
        "applications.Solicitud",
        on_delete=models.CASCADE,
        related_name="reclamaciones",
    )

    # Datos de la reclamación
    tipo = models.CharField(
        max_length=20,
        choices=TipoReclamacion.choices,
    )
    descripcion = models.TextField(
        help_text=_("Motivo de la reclamación"),
    )
    evidencia = models.FileField(
        upload_to="reclamaciones/%Y/%m/",
        blank=True,
        null=True,
    )

    # Estado y resolución
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PRESENTADA,
    )
    respuesta = models.TextField(
        blank=True,
        help_text=_("Fundamentación de la resolución"),
    )
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reclamaciones_resueltas",
    )
    fecha_resolucion = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Reclamación")
        verbose_name_plural = _("Reclamaciones")

    def __str__(self):
        return f"Reclamación {self.uuid} - {self.solicitud.radicado}"
```

### Modelo ReclamacionHistorial

```python
class ReclamacionHistorial(models.Model):
    """Historial de cambios de estado de una reclamación."""

    reclamacion = models.ForeignKey(
        Reclamacion,
        on_delete=models.CASCADE,
        related_name="historial",
    )
    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    observacion = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
```

### Transiciones de Estado

| Estado Actual | Evento | Estado Siguiente | Acción |
|--------------|--------|------------------|--------|
| PRESENTADA | iniciar_revision | EN_REVISION | Junta inicia revisión |
| EN_REVISION | resolver | RESUELTA | Junta acepta |
| EN_REVISION | rechazar | RECHAZADA | Junta rechaza |
| PRESENTADA | vencer | RECHAZADA | Sistema (plazo) |

### Reglas de Negocio

1. **Plazo**: 15 días hábiles desde publicación de resultados preliminares
2. **Owner**: Solo el aspirante de la solicitud puede crear reclamación
3. **Edición**: Solo en estado PRESENTADA
4. **Resolución**: Solo R-JUNTA puede resolver
5. **Auditoría**: Toda transición registrada en historial + auditoría CAP-022

### APIs Requeridas

- `GET /claims/` — Lista del usuario
- `POST /claims/crear/<uuid:solicitud>/` — Crear
- `GET /claims/<uuid:pk>/` — Detalle
- `PATCH /claims/<uuid:pk>/` — Editar (si PRESENTADA)
- `POST /claims/<uuid:pk>/resolver/` — Resolver (R-JUNTA)
- `GET /claims/admin/` — Lista admin (R-JUNTA)

### Notificaciones

| Evento | Destinatario | Canal |
|--------|--------------|-------|
| reclamación.presentada | Coordinación | In-app |
| reclamación.resuelta | Aspirante | In-app |
