# Tasks — CHG-207: Resultados Definitivos y Acto Administrativo

## 1. Modelo de Acto Administrativo

- [x] Crear modelo `ActoAdministrativo` en `apps/governance/models.py`
- [x] Crear modelo `SecuencialActo` para numeración
- [x] Crear migración
- [ ] Registrar en admin

## 2. Generador de Consecutivos

- [x] Crear servicio `generar_numero_acto(tipo)` en `apps/governance/services/`
- [x] Formato: `FODEJAS-YYYY-NNNNN`
- [x] Thread-safe con select_for_update

## 3. Vista de Listado Definitivo

- [x] Crear vista `ListadoDefinitivoView` en `apps/convocatories/views.py`
- [x] Generar ranking final (post-apelaciones)
- [ ] Mostrar en template

## 4. Generación de PDF

- [ ] Crear template HTML para acto administrativo
- [ ] Crear servicio `generar_pdf_acto(acto)`
- [ ] Usar WeasyPrint
- [ ] Almacenar hash SHA-256

## 5. Actos Modificatorios

- [ ] Soporte para tipo "MODIFICATORIO"
- [ ] Referencia al acto original
- [ ] Trail de correcciones

## 6. Publicación en Portal

- [ ] Crear vista pública de resultados definitivos
- [ ] Template para listado de beneficiarios
- [ ] Solo datos agregados (sin PII)

## 7. Tests

- [ ] Tests unitarios para generador de consecutivos
- [ ] Tests de integración para generación de PDF
- [ ] Tests end-to-end del flujo completo
