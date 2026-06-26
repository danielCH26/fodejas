## Context

FODEJAS es una plataforma Django 5 que ya implementó configuración por entorno con `django-environ` (inf-004-environments). Sin embargo, los secrets actualmente solo están en archivos `.env` que se distribuyen manualmente, sin validación automática ni estrategia de rotación.

El proyecto necesita cumplir con prácticas de seguridad que incluyen:
- Zero secrets en código/fixtures/commits
- Gestión centralizada de secrets para staging/production
- Detección automática de secrets accidentalmente committed
- Política documentada de rotación

## Goals / Non-Goals

**Goals:**
- Crear servicio abstracto de secrets (`SecretStore`) con interfaz clara
- Implementar `EnvSecretStore` para desarrollo local (lee de environment)
- Definir interfaz para `VaultSecretStore` (preparado para futuro)
- Integrar `detect-secrets` en pre-commit y CI
- Documentar política de rotación

**Non-Goals:**
- No implementar Vault/AWS Secrets Manager en esta iteración (solo preparar interfaz)
- No cambiar el sistema de autenticación existente
- No crear infraestructura de secrets (Vault cluster, AWS SM)
- No modificar el flujo de deploy existente

## Decisions

### 1. Arquitectura del servicio de secrets

**Decisión:** Crear `apps/core/secrets.py` con clase abstracta `SecretStore` y implementaciones concretas.

**Alternativas consideradas:**
- Usar directamente `django-environ` — demasiado simple, no permite swapping
- Usar `hvac` (Vault client) directamente — acoplamiento fuerte a Vault
- Usar `python-decouple` — similar a django-environ, no extensible

**Elección:** Patrón Strategy con `SecretStore` abstracto.

**Justificación:** Permite cambiar implementación sin cambiar código de negocio. Desarrollo usa `EnvSecretStore`, producción puede usar `VaultSecretStore` cuando esté disponible.

### 2. Interfaz del SecretStore

```python
class SecretStore(ABC):
    @abstractmethod
    def get(self, key: str) -> str: ...

    @abstractmethod
    def get_required(self, key: str) -> str:
        """Get secret or raise MissingSecretError"""

    @abstractmethod
    def list_keys(self) -> list[str]: ...
```

**Decisión:** Interfaz mínima con `get`, `get_required`, `list_keys`.

**Justificación:** Suficiente para Django settings. Fácil de mock en tests.

### 3. Detección de secrets en pre-commit

**Decisión:** Usar `detect-secrets` pre-commit hook + baseline file.

**Alternativas:**
- Solo CI — no bloquea commit, solo CI fail
- Git hooks personalizados — mantenimiento complejo
- Herramientas enterprise (GitGuardian) — overkill para el equipo

**Elección:** `detect-secrets` con baseline y pre-commit hook.

**Justificación:** Open source, mantenido por Yelp, integración fácil, falsos positivos configurables.

### 4. Baseline file strategy

**Decisión:** Crear `.secrets.baseline` con secrets conocidos ( Allowlisted) para development.

**Formato:**
```json
{
  "version": "0.1.0",
  "results": {
    "secret-name": {
      "type": "Secret Type",
      "verified": false,
      "line_numbers": [123],
      "comment": "Development only secret, not real"
    }
  }
}
```

**Justificación:** Permite que pre-commit pase durante desarrollo sin exponer secrets reales.

### 5. Ubicación del baseline

**Decisión:** `.secrets.baseline` en raíz del proyecto, versionado.

**Alternativas:**
- `.gitignore` el baseline — pierde historial de allowlist
- Archivo separado por entorno — complejidad innecesaria

**Elección:** Baseline versionado junto al código.

**Justificación:** Todos los developers ven qué está allowlisted. Cambios al baseline son auditable.

## Secrets a Gestionar

| Secret | Fuente | Staging | Production |
|--------|--------|---------|------------|
| `SECRET_KEY` | Generated | Generated | Generated |
| `DATABASE_URL` | Infra | Infra | Infra |
| `REDIS_PASSWORD` | Infra | Infra | Infra |
| `AWS_SECRET_ACCESS_KEY` | MinIO dev | S3 prod | S3 prod |
| `SMTP_PASSWORD` | None | IT provides | IT provides |

## Rotation Policy

| Secret | Rotation Period | Process |
|--------|-----------------|---------|
| `SECRET_KEY` | 90 days | Generate new, coordinate deploy |
| Database credentials | 180 days | DBA rotation, update Vault |
| Redis password | 90 days | Update via Vault |
| AWS keys | 180 days | AWS IAM rotation |
| SMTP password | 30 days | Request via IT |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Secrets committed before hook runs | CI check adicional; nunca confiar solo en pre-commit |
| Baseline contains fake secrets | Solo `.env.development.example` con valores dummy |
| Vault no disponible en dev | `EnvSecretStore` fallback para desarrollo local |
| Secrets en logs | `apps/core/logging.py` ya mascara PII (no secrets però) |

## Migration Plan

1. Crear `apps/core/secrets.py` con `SecretStore` abstracto y `EnvSecretStore`
2. Actualizar `config/settings.py` para usar `secrets.get_required()`
3. Crear `.pre-commit-config.yaml` con `detect-secrets`
4. Crear `.secrets.baseline` vacío (sin secrets allowlisted)
5. Agregar job en CI para verificar secrets
6. Documentar en CONTRIBUTING.md

## Open Questions

1. **¿Qué formato de Vault para futuro?**
   - HashiCorp Vault — estándar, auto-unsealing
   - AWS Secrets Manager — nativo AWS, IAM integration
   - **Decision pendiente**: depende de infraestructura

2. **¿Dónde almacenar secrets de producción?**
   - CI/CD pipeline secrets (GitHub Actions)
   - Vault
   - AWS SM / GCP SM
   - **Decision**: Preparar interfaz, validar con equipo de infraestructura
