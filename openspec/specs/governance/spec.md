# governance/spec.md — Actos Administrativos

## ADDED

### 3.1 Modelo ActoAdministrativo

```python
class ActoAdministrativo(models.Model):
    """Acto administrativo generado por la Junta."""

    class Tipo(models.TextChoices):
        RESOLUCION = "resolucion", _("Resolución")
        ACTA = "acta", _("Acta")
        MODIFICATORIO = "modificatorio", _("Acto Modificatorio")
        CERTIFICACION = "certificacion", _("Certificación")

    class Estado(models.TextChoices):
        BORRADOR = "borrador", _("Borrador")
        FIRMADO = "firmado", _("Firmado")
        PUBLICADO = "publicado", _("Publicado")
        ANULADO = "anulable", _("Anulado")

    # UUID
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # Numeración
    numero = models.CharField(max_length=30, unique=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)

    # Fechas
    fecha_expedicion = models.DateField()
    fecha_publicacion = models.DateTimeField(null=True, blank=True)

    # Contenido
    asunto = models.TextField()
    considerandos = models.JSONField(default=list)
    resolutivo = models.TextField()

    # Referencia para actos modificatorios
    acto_original = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="modificatorios",
    )

    # Archivo
    pdf = models.FileField(upload_to="actos/%Y/%m/", null=True, blank=True)
    pdf_sha256 = models.CharField(max_length=64, null=True, blank=True)

    # Estado
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)

    # Firmantes
    firmantes = models.JSONField(default=list)  # [{"nombre": "...", "rol": "..."}]

    # Metadata
    convocatoria = models.ForeignKey(
        "convocatories.Convocatory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="actos",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 3.2 Modelo SecuencialActo

```python
class SecuencialActo(models.Model):
    """Secuencial para numeración de actos administrativos."""

    tipo = models.CharField(max_length=20, unique=True)  # resolucion, acta, etc.
    anio = models.PositiveIntegerField()
    secuencia = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ["tipo", "anio"]
```

### 3.3 Servicio Generador de Consecutivos

```python
def generar_numero_acto(tipo: str) -> str:
    """
    Genera número de acto administrativo.
    Formato: FODEJAS-YYYY-NNNNN
    """
    from apps.governance.models import SecuencialActo
    from django.db import transaction

    anio = timezone.now().year

    with transaction.atomic():
        seq, created = SecuencialActo.objects.select_for_update().get_or_create(
            tipo=tipo,
            anio=anio,
            defaults={"secuencia": 0}
        )
        seq.secuencia += 1
        seq.save()

    return f"FODEJAS-{anio}-{seq.secuencia:05d}"
```

### 3.4 Servicio Generación PDF

```python
def generar_pdf_acto(acto: ActoAdministrativo) -> bytes:
    """
    Genera PDF del acto administrativo usando WeasyPrint.
    Returns: bytes del PDF
    """
    from weasyprint import HTML

    template = get_template("governance/acto_pdf.html")
    context = {"acto": acto}
    html_content = template.render(context)

    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes
```

### 3.5 Modelo ListadoDefinitivo

```python
class ListadoDefinitivo(models.Model):
    """Listado definitivo de beneficiarios publicado."""

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    convocatoria = models.OneToOneField(
        "convocatories.Convocatory",
        on_delete=models.CASCADE,
        related_name="listado_definitivo",
    )

    # Ranking final (lista de IDs de solicitudes)
    ranking = models.JSONField()  # [{"solicitud_id": "...", "puntaje": 95.5, "rank": 1}]

    # Acto administrativo que aprueba el listado
    acto = models.ForeignKey(
        ActoAdministrativo,
        on_delete=models.PROTECT,
        related_name="listados",
    )

    # Fechas
    fecha_publicacion = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)
```

## MODIFIED

### 4.1 Convocatory.Estado

Agregar estado:

```python
class Convocatory(models.Model):
    class Estado(models.TextChoices):
        # ...existing states...
        RESULTADOS_DEFINITIVOS = "resultados_definitivos", _("Resultados Definitivos")
```
