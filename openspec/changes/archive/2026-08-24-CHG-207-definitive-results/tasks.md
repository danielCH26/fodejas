# Tasks — CHG-207: Resultados Definitivos y Acto Administrativo

## 1. Modelo de Acto Administrativo

- [x] Crear modelo `ActoAdministrativo` en `apps/governance/models.py`
- [x] Crear modelo `SecuencialActo` para numeración
- [x] Crear migración
- [x] Registrar en admin

## 2. Generador de Consecutivos

- [x] Crear servicio `generar_numero_acto(tipo)` en `apps/governance/services/`
- [x] Formato: `FODEJAS-YYYY-NNNNN`
- [x] Thread-safe con select_for_update

## 3. Vista de Listado Definitivo

- [x] Crear vista `ListadoDefinitivoView` en `apps/convocatories/views.py`
- [x] Generar ranking final (post-apelaciones)
- [x] Mostrar en template

## 4. Generación de PDF

- [x] Crear template HTML para acto administrativo
- [x] Crear servicio `generar_pdf_acto(acto)`
- [x] Usar WeasyPrint
- [x] Almacenar hash SHA-256

## 5. Actos Modificatorios

- [x] Soporte para tipo "MODIFICATORIO"
- [x] Referencia al acto original
- [x] Trail de correcciones

## 6. Publicación en Portal

- [x] Crear vista pública de resultados definitivos
- [x] Template para listado de beneficiarios
- [x] Solo datos agregados (sin PII)

## 7. Tests

- [x] Tests unitarios para generador de consecutivos
- [x] Tests de integración para generación de PDF
- [x] Tests end-to-end del flujo completo

## Fixes Post-Verify (C-1 a C-5, W-1)

- [x] C-1: max_length insuficiente en Convocatory.estado (16→32)
- [x] C-2: guardar_pdf_acto no persistía archivo (usar ContentFile)
- [x] C-3: Mock de PuntajeTotal no funcionaba (parchear path correcto)
- [x] C-4: Test test_generar_numero_diferentes_tipos incorrecto
- [x] C-5: Tests E2E del flujo completo (scoring -> acto -> listado -> publicacion)
- [x] W-1: Quitar unique=True de SecuencialActo.tipo
