## Context

FODEJAS es una plataforma Django 5 con Celery para tareas async. Actualmente tiene logging básico de texto y no hay forma de:
- Rastrear errores en producción con contexto completo
- Medir latencia de endpoints o tareas Celery
- Verificar salud de la aplicación desde Kubernetes
- Exportar métricas a sistemas de monitoreo

El equipo de operaciones necesita observabilidad para responder a incidentes sin pedir logs directamente a desarrolladores.

## Goals / Non-Goals

**Goals:**
- Logging estructurado JSON para centralización en ELK/Loki
- Captura de errores con Sentry (contexto de usuario/sesión)
- Health checks para Kubernetes (liveness + readiness)
- Métricas Prometheus para Grafana (latencia, errores, uptime)
- Instrumentación de vistas Django y tareas Celery

**Non-Goals:**
- No implementar Grafana dashboards (configuración externa)
- No tracking de performance en Sentry (overhead)
- No métricas de negocio personalizadas (scope inicial)
- No distributed tracing (Zipkin/Jaeger) - futuro
- No modificar flujos de usuario existentes

## Decisions

### 1. Logging estructurado

**Decisión:** Usar `python-json-logger` + Django logging estructurado.

**Alternativas:**
- `structlog` — más potente pero curva de aprendizaje mayor
- logging manual JSON — mantenimiento complejo
- `loguru` — no integrado nativamente con Django

**Elección:** `python-json-logger` con formatter JSON estándar.

**Justificación:** Integración directa con Django logging, output compatible con ELK/Loki/Graylog.

### 2. Sentry integration

**Decisión:** Usar `sentry-sdk` con integración Django y Celery.

**Alternativas:**
- Raven ( old) — deprecated
- Integración manual con API — más trabajo, menos features
- Solo logs — no da contexto de errores en tiempo real

**Elección:** `sentry-sdk`.

**Justificación:** Instalación mínima, contexto automático de requests/sesión, source maps en CI.

### 3. Health checks

**Decisión:** Crear vistas dedicadas en `apps/core/health.py`.

**Estructura:**
- `/healthz` — Liveness: solo verifica que Django responde
- `/readyz` — Readiness: verifica DB + Redis + Sentry connectivity

**Justificación:** Separación clara para Kubernetes. Liveness es rápido, Readiness puede ser más lento (verifica dependencias).

### 4. Métricas Prometheus

**Decisión:** Usar `django-prometheus` para exportación automática.

**Lo que exporta automático:**
- Latencia de requests por vista
- Count de requests por código de respuesta
- Métricas de DB queries

**Lo que agregamos manualmente:**
- `celery_tasks_total` con status y nombre
- `celery_task_latency_seconds`
- Uptime de workers

**Justificación:**django-prometheus ya tiene exporters para lo común, solo agregar Celery.

### 5. Middleware de correlación

**Decisión:** Crear `apps/core/middleware.py` con:
- Request ID generation (UUID) + propagation via `X-Request-ID` header
- Logging context injection en thread local
- Métricas de latencia por request

**Justificación:** Sin request ID es imposible correlacionar logs entre servicios. Thread local permite acceso sin pasar contexto explícito.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-------------|
| Sentry overhead en producción | Solo errores, sampling en high-volume endpoints |
| Logging JSON llena disco | Rotación diaria + size limit en settings |
| Métricas exponen datos sensibles | `/metrics` protegido internamente, no expuesto público |
| Health checks muy lentos | `/readyz` con timeout 5s, fail fast |

## Migration Plan

1. Agregar dependencias (`sentry-sdk`, `python-json-logger`, `prometheus-client`, `django-prometheus`)
2. Crear `apps/core/logging_config.py` con formatter JSON
3. Crear `apps/core/middleware.py` con request ID
4. Actualizar `config/settings.py` para logging JSON en producción + Sentry
5. Crear `apps/core/health.py` con `/healthz` y `/readyz`
6. Agregar métricas Celery en `apps/core/celery.py` o `apps/core/metrics.py`
7. Registrar rutas en `config/urls.py`
8. Actualizar CI para verificar health endpoint responde

## Open Questions

1. **¿Autenticación en `/metrics`?**
   - Interno: sin auth (solo métricas técnicas)
   - Expuesto externo: necesitaría reverse proxy con auth
   - **Decisión**: `/metrics` solo accesible desde red interna (documentar)

2. **¿Sampling en Sentry?**
   - 100% de errores: sí
   - Transacciones (performance): no (deshabilitado)
   - **Decisión**: Solo error tracking, no performance

3. **¿Grafana externo o local?**
   - No implementado en esta iteración
   - Preparado: `/metrics` expuesto
   - **Decisión**: Equipo de operaciones configura Grafana separately
