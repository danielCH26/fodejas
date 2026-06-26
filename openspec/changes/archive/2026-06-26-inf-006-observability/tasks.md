## 1. Dependencies

- [x] 1.1 Add `python-json-logger` to dependencies in `pyproject.toml`
- [x] 1.2 Add `sentry-sdk` to dependencies
- [x] 1.3 Add `prometheus-client` to dependencies
- [x] 1.4 Add `django-prometheus` to dependencies

## 2. Logging Configuration

- [x] 2.1 Create `apps/core/logging_config.py` with JSON formatter for production
- [x] 2.2 Configure Django `LOGGING` setting to use JSON formatter when `IS_PRODUCTION`
- [x] 2.3 Test JSON logging output format manually

## 3. Request ID Middleware

- [x] 3.1 Create `apps/core/middleware.py` with `RequestIDMiddleware`
- [x] 3.2 Generate UUID4 when `X-Request-ID` header not present
- [x] 3.3 Add request ID to thread-local context for logging
- [x] 3.4 Add response header `X-Request-ID`
- [x] 3.5 Register middleware in `config/settings.py`

## 4. Sentry Integration

- [x] 4.1 Add `sentry_sdk.init()` in `config/settings.py` when `IS_PRODUCTION`
- [x] 4.2 Configure Sentry with Django integration and Celery integration
- [x] 4.3 Disable Sentry performance monitoring
- [x] 4.4 Add `sentry_sdk.set_tag` for environment info

## 5. Health Checks

- [x] 5.1 Create `apps/core/health.py` with `liveness` view returning HTTP 200
- [x] 5.2 Create `apps/core/health.py` with `readiness` view checking DB connection
- [x] 5.3 Add Redis connectivity check to readiness
- [x] 5.4 Add timeout (5s) to readiness checks
- [x] 5.5 Add health check URLs to `config/urls.py` (no auth required)
- [x] 5.6 Verify `/healthz` returns 200 without DB
- [x] 5.7 Verify `/readyz` returns 503 when DB down

## 6. Prometheus Metrics

- [x] 6.1 Add `django-prometheus` to installed apps in `config/settings.py`
- [x] 6.2 Create `apps/core/metrics.py` with Celery metrics (celery_tasks_total, celery_task_latency_seconds)
- [x] 6.3 Register Celery signal handlers for task completion
- [x] 6.4 Add `/metrics` URL to `config/urls.py`
- [x] 6.5 Verify `/metrics` returns Prometheus format

## 7. Verification

- [ ] 7.1 Verify JSON logs appear in staging with request_id correlation
- [ ] 7.2 Verify Sentry captures test exception (trigger manually)
- [ ] 7.3 Verify health endpoints work from kubectl exec
- [ ] 7.4 Verify Prometheus metrics are scrapeable by Grafana
