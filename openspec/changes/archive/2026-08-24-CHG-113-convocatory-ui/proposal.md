# CHG-113: Interfaz HTML para Gestión de Convocatorias

## Contexto

CHG-201 implementó el motor de convocatorias (CAP-002) con API REST, pero no existe interfaz HTML para que los administradores gestionen convocatorias desde el navegador.

## Capacidades afectadas

- **CAP-002** — Gestión de Convocatorias
- **CAP-022** — Bitácora de Auditoría

## Estado actual

El sistema tiene:
- `Convocatory` model con estados (borrador, publicada, en_inscripcion, etc.)
- API REST en `/api/convocatorias/`
- Servicios de transición de estado
- Vistas de solo lectura en el dashboard

**Falta**: Interfaz HTML completa para gestionar convocatorias.

## Cambios propuestos

### 1. Listado de Convocatorias

- Tabla con todas las convocatorias
- Filtros por estado, tipo, período
- Buscador por nombre o código
- Acciones: ver detalle, editar, cambiar estado

### 2. Crear Convocatoria

- Formulario con campos:
  - Nombre, código, tipo (técnico, tecnológico, pregrado, etc.)
  - Período académico
  - Monto en SMMLV
  - Duración máxima en semestres
  - Cupo total

### 3. Editar Convocatoria

- Modificar datos de la convocatoria
- Solo permitido en estado "borrador"

### 4. Cambiar Estado (FSM)

- Publicar (borrador → publicada)
- Abrir inscripciones (publicada → en_inscripcion)
- Cerrar inscripciones (en_inscripcion → en_verificacion)
- Publicar resultados (en_calificacion → definitiva)
- Cerrar convocatoria (definitiva → cerrada)

### 5. Ver Detalle

- Información completa de la convocatoria
- Configuración asociada
- Historial de estados

### 6. Integración con Auditoría

- Toda modificación queda registrada

## Criterios de aceptación

- [ ] Se muestra listado de convocatorias con filtros
- [ ] Se puede crear una nueva convocatoria
- [ ] Se puede editar una convocatoria en estado borrador
- [ ] Se puede cambiar el estado de la convocatoria
- [ ] Se muestra el detalle de la convocatoria
- [ ] Los cambios quedan registrados en auditoría
- [ ] Solo usuarios con rol apropiado pueden acceder

## Riesgos y fuera del alcance

- Interfaz de configuración de reglas (para futuro)
- Publicación automática de resultados
- Integración con otros sistemas
