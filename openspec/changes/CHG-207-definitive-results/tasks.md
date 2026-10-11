# Tasks — CHG-207: Resultados Definitivos y Acto Administrativo

## 1. Modelo de Acto Administrativo

- [x] Crear modelo `ActoAdministrativo` en `apps/governance/models.py`
- [x] Crear modelo `SecuencialActo` para numeración
- [x] Crear migración
- [x] Registrar en admin (pre-existing: ActoAdministrativo/ListadoDefinitivo registrados)

## 2. Generador de Consecutivos

- [x] Crear servicio `generar_numero_acto(tipo)` en `apps/governance/services/`
- [x] Formato: `FODEJAS-YYYY-NNNNN`
- [x] Thread-safe con select_for_update

## 3. Vista de Listado Definitivo

- [x] Crear vista `ListadoDefinitivoView` en `apps/convocatories/views.py`
- [x] Generar ranking final (post-apelaciones)
- [x] Mostrar en template (pre-existing: listado_detail.html + listado_publico.html)

## 4. Generación de PDF

- [x] Crear template HTML para acto administrativo (templates/governance/acto_pdf.html — encabezado institucional SED, firmantes, pie con verificación de hash)
- [x] Crear servicio `generar_pdf_acto(acto)` + `guardar_pdf_acto` (pre-existing; corregido bug: el contenido del FileField era `bytes` crudo — ahora `ContentFile`; el template real no existía y el fallback genérico tampoco → TemplateDoesNotExist en runtime)
- [x] Usar WeasyPrint (pre-existing; render real a validar en CI/contenedor — host dev sin GTK)
- [x] Almacenar hash SHA-256 (`pdf_sha256` verificado en `test_acto_pdf_portal.py::TestActoPdf`)

## 5. Actos Modificatorios

- [x] Soporte para tipo "MODIFICATORIO" (pre-existing: Tipo.MODIFICATORIO + ActoModificatorioCreateView, CHG-208)
- [x] Referencia al acto original (pre-existing: `acto_original` FK, CHG-208)
- [x] Trail de correcciones (vía auditoría CAP-022 + acto_original FK; trail dedicado de modificatorios pendiente post-MVP)

## 6. Publicación en Portal

- [x] Crear vista pública de resultados definitivos (pre-existing: ListadoPublicoView; gating verificado — solo listados con acto PUBLICADO, sin PII: rank/radicado top-10)
- [x] Template para listado de beneficiarios (pre-existing: listado_publico.html)
- [x] Solo datos agregados (sin PII) (verificado: el contexto arma dicts con rank/radicado únicamente)

## 7. Tests

- [x] Tests unitarios para generador de consecutivos (pre-existing: cobertura en test_modificatorio.py — numeración con secuencia modificatoria)
- [x] Tests de integración para generación de PDF (`test_acto_pdf_portal.py::TestActoPdf`: hash SHA-256 + contenido del HTML renderizado)
- [x] Tests end-to-end del flujo completo (`test_acto_pdf_portal.py::TestActoEndToEnd`: crear→firmar→PDF+hash→publicar→portal anónimo)
