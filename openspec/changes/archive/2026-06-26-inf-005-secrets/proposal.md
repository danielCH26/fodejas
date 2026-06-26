## Why

El proyecto FODEJAS necesita una estrategia formal de gestión de secrets para cumplir con las normas de seguridad y proteger información sensible. Aunque inf-004-environments estableció la configuración por entorno con variables de entorno, actualmente no existe un mecanismo para:

- Almacenar secrets de forma segura fuera del código
- Rotar secrets periódicamente
- Validar que no haya secrets committed en el repositorio
- Gestionar secrets en entornos de staging y producción de forma centralizada

Sin una gestión de secrets robusta, el proyecto es vulnerable a exposición accidental de credenciales.

## What Changes

- Implementar integración con **Django-environ** para lectura de secrets desde environment variables (continuando inf-004-environments)
- Crear servicio abstracto de secrets (`apps/core/secrets.py`) con implementación para desarrollo local y準備 para HashiCorp Vault/AWS Secrets Manager
- Agregar validación pre-commit para detectar secrets accidentalmente committed
- Documentar política de rotación de secrets
- Agregar validación CI/CD para verificar que no hay secrets en el código

## Capabilities

### New Capabilities
- `secrets-management`: Servicio abstracto de gestión de secrets con implementaciones para desarrollo y producción (vault)

### Modified Capabilities
- Ninguno (inf-004-environments ya estableció environment-config)

## Impact

- Nuevos archivos:
  - `apps/core/secrets.py` — servicio abstracto de secrets
  - `apps/core/tests/test_secrets.py` — pruebas unitarias
  - `.pre-commit-config.yaml` — configuración de detect-secrets
- Modificados:
  - `config/settings.py` — integrar servicio de secrets
  - `CONTRIBUTING.md` — agregar guía de gestión de secrets
- Dependencias: `detect-secrets` (ya en dev deps via pre-commit)

## Constraints (from AGENTS.md)

- **No integraciones externas** (SNIES, SISBÉN, OCCRE, bancos). La verificación es manual/externa. Pero sí se puede integrar con Vault o AWS Secrets Manager que son servicios internos de infraestructura.
- **Secrets fuera del código**: nunca en fixtures, commits ni logs
- **Retención 20 años** para expedientes contractuales
