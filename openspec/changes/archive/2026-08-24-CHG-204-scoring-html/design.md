# Design — CHG-204 Interfaz HTML para Scoring

## Arquitectura

```
/scoring/
├── models.py          # Evaluacion, PuntajeTotal
├── views.py          # Vistas de scoring
├── urls.py           # URLs con UUID
├── services/
│   └── scoring_service.py  # Lógica de cálculo
└── templates/scoring/
    ├── list.html     # Lista de evaluaciones
    ├── detail.html   # Evaluación por criterios
    ├── ranking.html  # Rankings
    └── export.html   # Exportación
```

## Decisiones de Diseño

### 1. Modelo Evaluacion por Criterio

- **Por qué**: Permite trazabilidad de cada evaluación
- **Cómo**: Una fila por criterio por solicitud
- **Beneficio**: Auditoría completa de qué evaluó quién

### 2. Pesos Configurables

- **Por qué**: Los criterios pueden variar por convocatoria
- **Cómo**: Leer de `ConfiguracionConvocatoria.criterios`
- **Trade-off**: Más complejo pero más flexible

### 3. Ranking en Base de Datos

- **Por qué**: consulted frequently
- **Cómo**: Campo en PuntajeTotal, calculado en Python
- **Trade-off**: Duplicación vs rendimiento

### 4. Regla Providencia en Query

- **Por qué**: Aplicar en ordenamiento SQL
- **Cómo**: `CASE WHEN municipio.codigo = 'PROVIDENCIA' THEN 0 ELSE 1 END`

## Permisos

| Rol | Acceso |
|-----|--------|
| R-COMITE | Evaluar y ver rankings |
| R-COORDINADOR | Ver rankings |
| R-ADMIN | Ver todo |

## Dependencias

- CHG-203 (requirements-check-html) — solicitudes verificadas
- CHG-106 (notifications) — notificar resultados
- Configuración de criterios en Convocatoria

## Externo

- WeasyPrint para PDF (ya configurado)
- openpyxl para Excel
