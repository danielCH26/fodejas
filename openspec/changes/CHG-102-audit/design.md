# Design — CHG-102-audit (CAP-022)

## Architecture Decision: Hash Chain Implementation

### Option A: Database-triggered hash
- Uses database triggers to calculate hash on insert
- **Pros**: Guaranteed consistency, works at DB level
- **Cons**: PostgreSQL-specific, complex to maintain

### Option B: Application-level hash (SELECTED)
- Calculate hash in Python before insert
- Query last record, calculate hash, insert atomically
- **Pros**: Portable, testable, Django-friendly
- **Cons**: Small race condition window (mitigated with transaction)

### Option C: Middleware-based
- Use Django middleware to capture all requests
- **Pros**: Captures all HTTP activity
- **Cons**: Doesn't capture model-level changes (signals needed anyway)

**Decision**: Option B — application-level hash with atomic transactions.

## Model Design

### AuditEvent Fields

```python
class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    timestamp = models.DateTimeField(db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_events'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity = models.CharField(max_length=100, db_index=True)
    entity_id = models.UUIDField(db_index=True)
    changes = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    module = models.CharField(max_length=50)
    previous_hash = models.CharField(max_length=64)
    current_hash = models.CharField(max_length=64, unique=True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['entity', 'entity_id']),
            models.Index(fields=['actor', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
```

### Hash Calculation

```python
def calculate_hash(timestamp, actor_id, action, entity, entity_id, changes, previous_hash):
    data = f"{timestamp.isoformat()}|{actor_id}|{action}|{entity}|{entity_id}|{changes}|{previous_hash}"
    return hashlib.sha256(data.encode()).hexdigest()
```

## Signal Configuration

### Auto-register signals

```python
# apps/audit/signals.py
def connect_audit_signals():
    for model in [CustomUser, Role, Permission, Convocatoria, ...]:
        post_save.connect(audit_signal_receiver, sender=model)
        post_delete.connect(audit_delete_receiver, sender=model)
```

## API Design

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/audit/events/` | GET | IsAuthenticated | List with filters |
| `/api/audit/events/{uuid}/` | GET | IsAuthenticated | Event detail |
| `/api/audit/verify/` | GET | IsAdminUser | Verify chain |

### Serializers

```python
class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = '__all__'
```

### Views

- `AuditEventListView` — paginated list with filters
- `AuditEventDetailView` — single event
- `AuditChainVerifyView` — verify integrity

## Performance Considerations

1. **Indexes**: Added on timestamp, entity, entity_id, actor
2. **Partitioning**: Future consideration for 20-year retention
3. **JSON storage**: Changes field is JSON, indexed by specific keys in queries

## Security

- Only authenticated users can query audit log
- Only admin users can verify chain
- IP and user agent captured but PII-minimized
