## ADDED Requirements

### Requirement: Termination causes management
The system SHALL support all termination causes defined in Art. 14 Decreto 0372/2025: abandono injustificado, retiro voluntario, finalización de periodos financiados, adulteración o información falsa, sanción disciplinaria/académica, promedio < 3.5 acumulado, y muerte.

#### Scenario: Create termination request
- **WHEN** a user creates a termination request for a legalized process
- **THEN** system creates a TerminationRequest with PENDIENTE status

#### Scenario: Approve termination request
- **WHEN** admin reviews and approves the termination request
- **THEN** status changes to TERMINADO and linked process is marked as terminated

### Requirement: Disbursement termination
The system SHALL support disbursement termination causes per Art. 15 Decreto 0372/2025, including: 2 semestres consecutivos de suspensión, no renovación por más de 2 períodos, promedio bajo por más de 2 períodos.

#### Scenario: Auto-terminate disbursements after suspension
- **WHEN** 2 consecutive semesters pass with suspended disbursements
- **THEN** system SHALL create a disbursement termination request automatically

### Requirement: Termination history tracking
The system SHALL maintain complete audit trail of all termination requests and resolutions.

#### Scenario: View termination history
- **WHEN** user requests termination history for a process
- **THEN** system returns all termination requests with timestamps and resolutions
