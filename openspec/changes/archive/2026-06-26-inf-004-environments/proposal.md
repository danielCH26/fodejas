## Why

El proyecto FODEJAS necesita una estrategia clara de configuración por entorno (development, staging, production) siguiendo los principios de **12-factor app**. Actualmente existe un `.env.example` genérico pero no hay separación clara de configuraciones por entorno, lo que puede llevar a errores de configuración en despliegue.

## What Changes

- Definir tres entornos: `development`, `staging`, `production`
- Crear archivos `.env.example` por entorno con valores apropiados
- Implementar configuración 12-factor con variables de entorno como fuente única de verdad
- Separar secretos de configuración (no hardcodear en código)
- Configurar Django settings para leer de environment variables
- Documentar las variables requeridas y opcionales por entorno

## Capabilities

### New Capabilities
- `environment-config`: Configuración parametrizada por entorno (dev/staging/prod) con archivos .env.example y soporte 12-factor

### Modified Capabilities
- Ninguno (configuración, no comportamiento)

## Impact

- Nuevos archivos:
  - `.env.development.example` — configuración de desarrollo
  - `.env.staging.example` — configuración de staging
  - `.env.production.example` — configuración de producción
  - `config/settings/environments/` — módulos de settings por entorno
- Modificados:
  - `config/settings/base.py` — integración con 12-factor
  - `.env.example` — actualizado como referencia genérica
- Dependencias: python-dotenv (ya en uso), django-environ (opcional)
