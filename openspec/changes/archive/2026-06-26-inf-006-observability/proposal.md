## Why

FODEJAS necesita observabilidad en producción para diagnosticar errores, monitorear rendimiento y detectar problemas antes de que afecten usuarios. Actualmente no existe trazabilidad centralizada, ni manejo de errores en tiempo real, ni métricas accesibles para operaciones.

## What Changes

- Agregar logging estructurado en formato JSON para consumo por sistemas de centralización de logs (ELK, Loki)
- Integrar Sentry para captura y agregación de errores con contexto de usuario/sesión
- Agregar endpoint `/healthz` para liveness probe (¿está vivo el proceso?)
- Agregar endpoint `/readyz` para readiness probe (¿está listo para recibir tráfico?)
- Exponer métricas Prometheus en `/metrics` para scraping por Grafana
- Instrumentar vistas de Django y tareas Celery con métricas básicas (latencia, count, errors)

## Capabilities

### New Capabilities

- `observability-logging`: Logging estructurado JSON con correlación de requests
- `observability-error-tracking`: Integración con Sentry para errores
- `observability-health-checks`: Endpoints `/healthz` y `/readyz` para Kubernetes probes
- `observability-metrics`: Métricas Prometheus exportadas via `/metrics`

### Modified Capabilities

- Ninguno (no cambia specs existentes)

## Impact

- Nuevos archivos:
  - `apps/core/logging_config.py` — configuración de logging estructurado
  - `apps/core/middleware.py` — middleware de correlación y métricas
  - `apps/core/health.py` — views de health checks
  - `apps/core/metrics.py` — exporter de métricas Prometheus
  - `config/urls.py` — rutas de health y metrics
- Modificados:
  - `config/settings.py` — agregar configuración de Sentry y logging JSON
- Dependencias nuevas: `sentry-sdk`, `prometheus-client`, `django-prometheus`

## Constraints

- **No integración directa con Grafana Cloud** — Se expone `/metrics` en formato Prometheus; Grafana se configura externamente
- **Sentry solo para errores** — No tracking de performance (para no agregar latencia)
- **Métricas básicas** — Solo latencia de requests, count de errores, uptime de Celery workers
- **Sin impacto en rendimiento** — Logging async, sampling acceptable en producción
