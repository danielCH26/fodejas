# Spec — CHG-113: Interfaz HTML para Gestión de Convocatorias

## Requisitos

### REQ-001: Listado de Convocatorias

- Mostrar todas las convocatorias en tabla
- Columns: nombre, código, tipo, período, estado, fecha_apertura, acciones
- Filtros: por estado, tipo, período
- Search: por nombre o código
- Acciones por fila: ver detalle, editar, cambiar estado

### REQ-002: Crear Convocatoria

- Formulario con validaciones
- Campos requeridos: nombre, código, tipo, período, monto, duración, cupo
- Solo accesible para R-ADMIN y R-COORDINADOR

### REQ-003: Editar Convocatoria

- Editar datos de la convocatoria
- Solo permitido cuando estado = "borrador"
- Validar que no haya inscripciones asociadas

### REQ-004: Cambiar Estado (FSM)

- Botones de acción según estado actual
- Transiciones válidas:
  - borrador → publicada (publicar)
  - publicada → en_inscripcion (abrir_inscripciones)
  - en_inscripcion → en_verificacion (cerrar_inscripciones)
  - en_verificacion → en_calificacion (iniciar_calificacion)
  - en_calificacion → definitiva (publicar_resultados)
  - definitiva → cerrada (cerrar)

### REQ-005: Ver Detalle

- Información completa de la convocatoria
- Historial de cambios de estado
- Lista de configuraciones asociadas

### REQ-006: Permisos

- Solo R-ADMIN y R-COORDINADOR pueden crear/editar
- Solo R-ADMIN puede cambiar a estado "cerrada"

## Escenarios

### ESC-001: Crear convocatoria exitosamente

1. Usuario entra a /convocatorias/
2. Hace clic en "Nueva Convocatoria"
3. Llena el formulario
4. Sistema crea en estado "borrador"
5. Redirige al listado

### ESC-002: Publicar convocatoria

1. Usuario en detalle de convocatoria en estado "borrador"
2. Hace clic en "Publicar"
3. Sistema verifica que tenga configuración válida
4. Cambia estado a "publicada"
5. Registra en auditoría
