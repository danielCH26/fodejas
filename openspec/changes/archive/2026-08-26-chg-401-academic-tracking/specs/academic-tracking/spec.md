## ADDED Requirements

### Requirement: Academic record management
The system SHALL maintain academic records for each legalized beneficiary, tracking their semester grades and cumulative average.

#### Scenario: Create academic record
- **WHEN** admin creates an academic record for a legalized process
- **THEN** system creates an AcademicRecord with ACTIVO status

### Requirement: Grade entry
The system SHALL allow entering grades per semester with course name, credits, and grade (0-5).

#### Scenario: Add semester grades
- **WHEN** admin enters grades for a semester
- **THEN** system calculates semester average and updates cumulative average

### Requirement: Minimum average validation
The system SHALL validate the minimum 3.5 cumulative average requirement per Art. 16 Decreto 0372/2025.

#### Scenario: Validate average
- **WHEN** cumulative average is calculated
- **THEN** system updates status based on threshold:
  - >= 3.5: ACTIVO
  - 3.0 - 3.49: ACADEMICO_BAJO
  - < 3.0: SUSPENDIDO

### Requirement: Early warning alerts
The system SHALL generate alerts when a beneficiary falls below the minimum average threshold.

#### Scenario: Alert on low average
- **WHEN** cumulative average drops below 3.5
- **THEN** system creates an alert for admin review

### Requirement: Academic suspension trigger
The system SHALL automatically trigger suspension review after 2 consecutive semesters below 3.5.

#### Scenario: Auto-trigger suspension
- **WHEN** 2 consecutive semesters are below 3.5
- **THEN** system marks status as SUSPENDIDO and alerts admin
