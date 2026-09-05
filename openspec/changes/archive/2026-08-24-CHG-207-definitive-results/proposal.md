# CHG-207: Resultados Definitivos y Acto Administrativo

## Contexto

Una vez procesadas las reclamaciones (CHG-205) y apelaciones (CHG-206), la Junta debe aprobar el listado definitivo de beneficiarios y emitir el acto administrativo correspondiente.

Este change implementa:
1. Generación del listado definitivo de beneficiarios
2. Emisión del acto administrativo con numeración centralizada
3. Publicación del listado en el portal
4. Corrección de errores formales (Art. 45 CPACA)

## Capacidades afectadas

- CAP-008 — Resultados definitivos y acto administrativo
- CAP-017 — Sesiones de Junta (actas firmadas)
- CAP-029 — Firma electrónica de documentos

## Reglas de negocio afectadas

- project.md §11.3 — Criterios de calificación (ranking por municipio)
- project.md §10.1 — Flujo de resultados definitivos
- Manual Operativo Art. 45 — Corrección de errores formales

## Cambios propuestos

### 1. Listado Definitivo

- Generar ranking final после resuelto apelaciones
- Incluir solo solicitudes en estado VERIFICADA
- Ordenar por puntaje total (mayor a menor)
- Aplicar regla de Providencia Isla (cupo especial)
- Publicar en el portal público

### 2. Acto Administrativo

- Modelo `ActoAdministrativo` con:
  - Tipo (RESOLUCION, ACTA, etc.)
  - Número secuencial (FORMATO: FODEJAS-AAAA-NNNNN)
  - Fecha de expedición
  - Asunto
  - Considerandos (JSON)
  - Firmantes
  - Archivo PDF firmado
  - Hash SHA-256

### 3. Numeración Centralizada

- Generador de consecutivos por tipo
- Formato: `<prefijo>-<yyyy>-<consecutivo>`
- Almacenar en modelo `SecuencialActo`

### 4. Corrección de Errores (Art. 45 CPACA)

- Nuevo tipo de acto: "MODIFICATORIO"
- Referencia al acto original
- Trail de correcciones

## Criterios de aceptación

- [ ] La Junta puede generar el listado definitivo desde el admin
- [ ] El acto administrativo se numera automáticamente
- [ ] El PDF del acto se genera con WeasyPrint
- [ ] El hash SHA-256 se almacena
- [ ] El listado se publica en el portal público
- [ ] Se puede crear un acto modificatorio para correcciones

## Pruebas

- Unitarias: generación de consecutivos, hash SHA-256
- Integración: generación de PDF, publicación del listado
- End-to-end: flujo completo desde scoring hasta acto administrativo

## Riesgos y fuera del alcance

- **Riesgo**: Generación de PDF con WeasyPrint (compatibilidad)
- **Fuera**: Firma electrónica con prestador certificado (CAP-029 futuro)
- **Fuera**: Notificaciones automáticas (CAP-019)
