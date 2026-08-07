## Context

Después de la legalización (CHG-302), los beneficiarios esperan sus desembolsos. El proceso requiere firmas autorizadas y coordinación con Tesorería. Actualmente no existe módulo de tesorería.

## Goals / Non-Goals

**Goals:**
- Autorización de pagos con doble firma (Presidente JA + Sec. Educación)
- Orden radicada en Tesorería con 4 adjuntos normativos
- Vista de conciliación manual
- Trazabilidad completa

**Non-Goals:**
- Integración con sistemas bancarios
- Procesamiento automático de pagos
- Generación de comprobantes (manual)

## Decisions

### D1: Modelo de Autorización de Desembolso

Se creará `DisbursementAuthorization` con:
- Referencia a LegalizationProcess
- Estados: PENDIENTE, AUTORIZADO, ORDENADO, PAGADO, RECHAZADO
- Campos para firmas autorizadas
- Referencia a orden de Tesorería

**Alternativa descartada**: Extender LegalizationProcess → Mezcla responsabilidades.

### D2: Conciliación Manual

Tesorería marca el pago como realizado y adjunta comprobante. No hay integración automática con banco.

**Alternativa descartada**: Integración bancaria → Fuera del alcance (regla AGENTS.md).

## Risks / Trade-offs

- [Risk] Plazo de 5 días hábiles de Tesorería → Mitigation: Alertas automáticas
- [Risk] Falta de comprobante → Mitigation: Validación en UI

## Migration Plan

1. Crear app treasury si no existe
2. Crear modelos
3. Crear vistas y URLs
4. No hay datos legacy
