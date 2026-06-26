## ADDED Requirements

### Requirement: Automated base backups

The system SHALL perform automated base backups of PostgreSQL to S3-compatible storage.

#### Scenario: Daily base backup occurs
- **WHEN** the backup schedule triggers
- **THEN** `pg_basebackup` SHALL create a full backup
- **AND** the backup SHALL be stored in S3 bucket `fodejas-backups`
- **AND** backup filename SHALL include timestamp

#### Scenario: Backup retention policy
- **WHEN** base backups older than 7 days exist
- **THEN** they SHALL be automatically deleted
- **AND** only the most recent 7 backups SHALL be retained

### Requirement: WAL archiving

The system SHALL continuously archive WAL segments for point-in-time recovery.

#### Scenario: WAL archiving enabled
- **WHEN** PostgreSQL starts in production
- **THEN** `wal_level` SHALL be set to `replica`
- **AND** `archive_mode` SHALL be set to `on`
- **AND** WAL segments SHALL be archived to S3

#### Scenario: WAL retention
- **WHEN** WAL archives older than 30 days exist
- **THEN** they SHALL be automatically deleted
- **AND** point-in-time recovery SHALL be possible up to 30 days

### Requirement: Backup verification

The system SHALL verify backup integrity.

#### Scenario: Backup integrity check
- **WHEN** a backup is completed
- **THEN** backup verification script SHALL run
- **AND** SHALL report success or failure

#### Scenario: Manual restore test
- **WHEN** manual restore test is triggered
- **THEN** a test database SHALL be restored from latest backup
- **AND** basic queries SHALL be executed to verify integrity

### Requirement: Backup monitoring

The system SHALL monitor backup jobs and alert on failures.

#### Scenario: Backup job failure alert
- **WHEN** a backup job fails
- **THEN** an alert SHALL be sent to operations team
- **AND** alert SHALL include job name and error details

#### Scenario: Backup completion notification
- **WHEN** a backup completes successfully
- **THEN** a notification SHALL be logged
- **AND** SHALL include backup size and duration
