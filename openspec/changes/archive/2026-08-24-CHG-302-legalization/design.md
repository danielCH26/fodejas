## Context

Después de la publicación del listado definitivo (CHG-207), los beneficiarios deben formalizar su crédito. El Decreto 0372/2025 Art. 8 requiere documentación formal. Actualmente no existe un módulo para gestionar estos documentos.

## Goals / Non-Goals

**Goals:**
- Gestionar ciclo de vida de documentos de legalización
- Generar PDFs de pagaré, carta de instrucciones y contrato
- Integrar con CHG-301 para firma electrónica
- Mantener trazabilidad completa en auditoría

**Non-Goals:**
- Integración con sistemas bancarios
- Generación automática de contratos (plantillas manuales)
- Envío automático de notificaciones (CAP-019 diferido)

## Decisions

### D1: Modelos Separados por Tipo de Documento

Se creará un modelo `LegalDocument` con campo `document_type` (PAGARE, CARTA_INSTRUCCIONES, CONTRATO). Esto permite:
- Unificar lógica de workflow
- Estados independientes por documento
- Extensibilidad para nuevos documentos

**Alternativa descartada**: Modelos separados (LegalizationPromissoryNote, etc.) → Duplicación de código.

### D2: PDFs como Attachments, No Generados en Tiempo Real

Los PDFs se generan una vez y se almacenan como attachments. La verificación usa hash SHA-256.

**Alternativa descartada**: Generación on-demand → Mayor carga, menor trazabilidad.

### D3: Workflow de Estados

```
PENDIENTE → FIRMADO → LEGALIZADO
              ↓
         CANCELADO
```

**Alternativa descartada**: Estados más granulares → Complejidad innecesaria para MVP.

## Risks / Trade-offs

- [Risk] Beneficiario no firma a tiempo → Mitigation: Notificaciones automáticas (futuro)
- [Risk] Documento modificado después de firma → Mitigation: Hash post-firma en auditoría

## Migration Plan

1. Crear modelos LegalDocument, LegalizationProcess
2. Crear servicio de generación de PDFs
3. Integrar con signer (CHG-301)
4. Crear vistas para gestión
5. No hay datos legacy que migrar
