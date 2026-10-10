"""Generación de PDF para actos administrativos (CHG-207)."""
import hashlib

from django.template.loader import get_template


def generar_pdf_acto(acto) -> bytes:
    """
    Genera PDF del acto administrativo usando WeasyPrint.

    Args:
        acto: Instancia de ActoAdministrativo

    Returns:
        Bytes del PDF generado

    Raises:
        ImportError: Si WeasyPrint no está instalado
    """
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise ImportError(
            "WeasyPrint no está instalado. Instala con: pip install weasyprint"
        ) from exc

    # Cargar template
    try:
        template = get_template("governance/acto_pdf.html")
    except Exception:
        # Template genérico si no existe
        template = get_template("governance/acto_pdf_generic.html")

    # Renderizar contexto
    context = {
        "acto": acto,
        "fecha_formato": acto.fecha_expedicion.strftime("%d de %B de %Y") if acto.fecha_expedicion else "",
    }
    html_content = template.render(context)

    # Generar PDF
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


def guardar_pdf_acto(acto) -> str:
    """
    Genera y guarda el PDF de un acto administrativo.

    Args:
        acto: Instancia de ActoAdministrativo

    Returns:
        Hash SHA-256 del PDF generado
    """
    # Generar PDF
    pdf_bytes = generar_pdf_acto(acto)

    # Calcular hash SHA-256
    sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # Guardar archivo
    filename = f"{acto.numero}.pdf"
    acto.pdf.save(filename, type(pdf_bytes)(pdf_bytes))
    acto.pdf_sha256 = sha256_hash
    acto.save()

    return sha256_hash
