## Context

This change implements CAP-011 (Seguimiento Académico de Beneficiarios) as defined in project.md. After a beneficiary receives disbursements, their academic progress must be tracked to ensure compliance with Art. 16 Decreto 0372/2025 (minimum 3.5 average).

The academic_tracking app already exists but has no models or services. We need to build the academic tracking functionality from scratch.

## Goals / Non-Goals

**Goals:**
- Track semester grades and calculate cumulative average
- Validate minimum 3.5 average requirement per Art. 16
- Generate alerts for at-risk beneficiaries (below 3.5)
- Track academic probation and suspension triggers
- Provide admin interface for managing academic records

**Non-Goals:**
- Integration with university systems (manual upload)
- Automated notifications (CAP-019)
- Grade validation against external systems
- Acompañamiento psicosocial (CAP-012)

## Decisions

1. **Model Structure**: Use separate models for AcademicRecord and GradeEntry
   - AcademicRecord: overall tracking per legalization process
   - GradeEntry: individual semester grades

2. **Average Calculation**: Use cumulative weighted average
   - Track each semester's average
   - Calculate cumulative from all semesters

3. **Alert Thresholds**:
   - Green: >= 3.5 average
   - Warning: 3.0 - 3.49 (risk)
   - Critical: < 3.0 (academic probation)

4. **Status Workflow**:
   - ACTIVO: Normal, meeting requirements
   - ACADEMICO_BAJO: Below 3.5 average
   - SUSPENDIDO: Academic suspension triggered
   - GRADUADO: Completed studies

## Risks / Trade-offs

- [Risk] Manual grade entry errors → Mitigation: Admin review workflow
- [Risk] Cumulative average calculation → Mitigation: Store each semester, recalculate on demand
- [Risk] Too many alerts → Mitigation: Configurable thresholds per convocation

## Migration Plan

1. Create models and migrations
2. Add admin interfaces
3. Create services for grade management
4. Add URL routes
5. Run tests

No backward compatibility needed - this is net new functionality.
