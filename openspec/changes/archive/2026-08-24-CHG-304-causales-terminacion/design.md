## Context

This change implements CAP-015 (Terminación del Convenio y Causales) and CAP-016 (Sanciones, Reintegros y Cobro Coactivo) as defined in project.md §11.6 and §11.7.

The condonation app already exists but has no models or services. We need to build the termination and sanction workflow from scratch.

## Goals / Non-Goals

**Goals:**
- Implement termination causes (Art. 14 Decreto 0372/2025): abandono, retiro voluntario, finalización, información falsa, sanciones, promedio < 3.5, muerte
- Implement disbursement termination (Art. 15 Decreto 0372/2025): 2 semestres suspendidos, no renovación > 2 períodos, promedio < 3.5 por > 2 períodos
- Implement sanctions and reintegration (Art. 17 Decreto 0372/2025): reembolso total + IPC, justificaciones válidas, procedimiento de apelación
- Track termination history for audit purposes

**Non-Goals:**
- Cobro coactivo (will be handled externally by tesorería)
- Multidioma (CAP-030)
- Portal de transparencia (CAP-021)

## Decisions

1. **Model Structure**: Use separate models for TerminationRequest and Sanction to keep concerns separated
   - TerminationRequest: tracks cause, status, documents, resolution
   - Sanction: tracks reintegration amount, payment status, justification

2. **Status Workflow**: Use Django's TextChoices for consistent state transitions
   - Termination: PENDIENTE -> EN_SESION -> TERMINADO / RECHAZADO
   - Sanction: PENDIENTE -> EN_REVISION -> APROBADA / RECHAZADA -> PAGADA / CONDONADA

3. **Justification Validation**: Allow only predefined justifications per Art. 17 (enfermedad grave, accidente, emergencia familiar, traslado)

4. **IPC Update**: Calculate IPC adjustment annually using official data (manual input for now)

5. **Link to Legalization**: Termination/Sanction linked to LegalizationProcess for complete audit trail

## Risks / Trade-offs

- [Risk] Complex state transitions → Mitigation: Explicit transition validation in services
- [Risk] IPC calculation accuracy → Mitigation: Manual input with validation, future integration
- [Risk] Cascade effects on other modules → Mitigation: Soft delete pattern, audit logging

## Migration Plan

1. Create models and migrations
2. Add admin interfaces
3. Create services for workflow
4. Add URL routes
5. Run tests

No backward compatibility needed - this is net new functionality.

## Open Questions

- Should termination automatically trigger sanction process? (Decision: No - separate workflows)
- How to handle appeals? (Decision: Link to existing claims app)
