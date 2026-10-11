# Tasks — CHG-502: Conflictos de Interés

## 1. Modelos
- [x] 1.1 `DeclaracionConflicto` (miembro_sesion, punto, texto,
      estado PENDIENTE/APROBADA/RECHAZADA, revisado_por/at)
- [x] 1.2 `VotoImpedimento` (declaracion, miembro votante ≠ declarante,
      a_favor, unique)
- [x] 1.3 Migraciones

## 2. Servicios
- [x] 2.1 `declarar_conflicto` (self, punto abierto, PENDIENTE bloquea voto)
- [x] 2.2 `votar_impedimento` (demás presentes; mayoría mitad+1 resuelve)
- [x] 2.3 Integración en `registrar_voto` (bloqueo PENDIENTE/APROBADA)
- [x] 2.4 Auditoría CAP-022 (declarar/votar/resolver)

## 3. API
- [x] 3.1 Actions `declarar_conflicto` (self) y `votar_impedimento`
- [x] 3.2 Tests de API y gating

## 4. Testing
- [x] 4.1 Unitarias: bloqueos, mayoría, exclusión, declarante≠votante
- [x] 4.2 Suite verde en sqlite y PostgreSQL


## Batch notes (2026-10-11)

- Implementado completo: modelos + servicios + integración en
  registrar_voto (chequeo COI extraído a `_voting_blockers`) + API
  (declarar_conflicto self-service, votar_impedimento) + 15 tests.
- La resolución del impedimento usa mayoría mitad+1 de los presentes
  habilitados excluyendo al declarante.
