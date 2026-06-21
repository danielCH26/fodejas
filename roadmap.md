# roadmap.md — Hoja de Ruta OpenSpec

> Hoja de ruta para implementar la **Plataforma FODEJAS** bajo la
> metodología **OpenSpec**. Define fases, capacidades a entregar en cada
> una, dependencias, criterios de salida y cambios (`changes/<id>/`) que
> se abrirán para materializar cada capacidad.
>
> Este roadmap **no contiene detalles de implementación**: cada cambio
> se concreta en su propio `proposal.md` + `tasks.md` + delta en
> `specs/<capability>/spec.md`, siguiendo las reglas de `AGENTS.md` §3
> y §6.

---

## Tabla de Contenido

1. [Principios de la Hoja de Ruta](#1-principios-de-la-hoja-de-ruta)
2. [Visión por Fases](#2-visión-por-fases)
3. [Convenciones de Cambios (CHG / INF)](#3-convenciones-de-cambios-chg--inf)
4. [Fase 0 — Infraestructura](#4-fase-0--infraestructura)
5. [Fase 1 — Fundamentos de Aplicación](#5-fase-1--fundamentos-de-aplicación)
6. [Fase 2 — Convocatoria Piloto](#6-fase-2--convocatoria-piloto)
7. [Fase 3 — Legalización y Pagos](#7-fase-3--legalización-y-pagos)
8. [Fase 4 — Seguimiento y Cierre](#8-fase-4--seguimiento-y-cierre)
9. [Fase 5 — Gobernanza, Transparencia y Mejoras](#9-fase-5--gobernanza-transparencia-y-mejoras)
10. [Mapa de Dependencias entre Capacidades](#10-mapa-de-dependencias-entre-capacidades)
11. [Capacidades por Fase (Resumen)](#11-capacidades-por-fase-resumen)
12. [Riesgos Globales y Mitigaciones](#12-riesgos-globales-y-mitigaciones)
13. [Criterios Globales de Aceptación del Proyecto](#13-criterios-globales-de-aceptación-del-proyecto)
14. [Convenciones de Nombrado para Cambios](#14-convenciones-de-nombrado-para-cambios)

---

## 1. Principios de la Hoja de Ruta

1. **Cada capacidad se entrega como un cambio OpenSpec completo**
   (`proposal.md` + `tasks.md` + delta en `specs/`) — no se hace
   código sin propuesta aprobada.
2. **Una capacidad por cambio** (o un grupo pequeño y cohesivo de
   capacidades que no tengan sentido por separado).
3. **Las fases son secuenciales**, pero dentro de una fase algunos
   cambios pueden ser paralelos si no comparten dependencias.
4. **La infraestructura (Fase 0) es prerrequisito de todo lo demás**:
   no se escribe código de aplicación hasta que el repo, los entornos,
   el CI/CD y la observabilidad estén operativos.
5. **Los fundamentos (Fase 1) son prerrequisito del valor de negocio**:
   auth, auditoría, catálogos, configuración por convocatoria y
   habeas data.
6. **El primer entregable de valor de negocio** es la **Fase 2**
   (convocatoria piloto), que debe permitir ejecutar la convocatoria
   "Reconocimiento a la Excelencia" end-to-end sin papel.
7. **Las integraciones externas (SNIES, SISBÉN, OCCRE, bancos) NO
   entran al roadmap**: la verificación es manual/externa y la
   transacción bancaria la hace Tesorería fuera de la plataforma
   (ver `AGENTS.md` §6 regla 2).
8. **Los plazos normativos** (5 SMLMV, 10 semestres, 5 días hábiles
   de Tesorería, 30 días calendario de exoneraciones, etc.) están
   fijados por el Decreto 0372/2025 y no se negocian en este roadmap.
9. **Trazabilidad inmutable desde el día 1** (CAP-022 entra en
   Fase 1, pero la Fase 0 ya deja la infraestructura para soportar
   logs y métricas).

---

## 2. Visión por Fases

```
┌──────────────────────────────────────────────────────────────────┐
│  FASE 0 — INFRAESTRUCTURA                                       │
│  Repo, Docker, CI/CD, entornos, secrets, observabilidad,        │
│  base de datos, storage, email, seguridad, DR                   │
│  → Plataforma desplegable y observable desde el día 1           │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  FASE 1 — FUNDAMENTOS DE APLICACIÓN                             │
│  Auth + RBAC + Auditoría + Catálogos + Config. Convocatoria     │
│  → Base técnica y de cumplimiento                                │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  FASE 2 — CONVOCATORIA PILOTO                                   │
│  "Reconocimiento a la Excelencia" end-to-end sin papel          │
│  → Inscripción → Verificación → Scoring → Reclamaciones →       │
│    Resultados definitivos                                        │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  FASE 3 — LEGALIZACIÓN Y PAGOS                                  │
│  Pagaré, contrato, firma electrónica, autorización de           │
│  desembolsos y conciliación con Tesorería                       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  FASE 4 — SEGUIMIENTO Y CIERRE                                  │
│  Académico, psicosocial, condonación, sanciones, cobro          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  FASE 5 — GOBERNANZA, TRANSPARENCIA Y MEJORAS                   │
│  Sesiones, conflictos, reportes, portal público, impacto,       │
│  auditoría externa, multidioma                                   │
└──────────────────────────────────────────────────────────────────┘
```

> **Caso de uso ancla**: la **Convocatoria Cerrada "Reconocimiento a
> la Excelencia" 2026-1** (descrita en `project.md` §12) es el caso
> de referencia. La Fase 2 debe permitir ejecutarla completa.

---

## 3. Convenciones de Cambios (CHG / INF)

Existen dos familias de cambios OpenSpec:

- **`INF-NNN-<slug>`** → cambios de **infraestructura** (Fase 0).
- **`CHG-NNN-<slug>`** → cambios de **aplicación/dominio** (Fases 1–5).

Cada cambio produce:

```
openspec/changes/<INF|CHG>-NNN-<slug>/
├── proposal.md
├── tasks.md
├── design.md      # opcional
└── specs/<capability>/spec.md   # delta (o specs/infra/... para INF)
```

Convenciones de numeración:

- `INF-0xx` → infraestructura base (Fase 0).
- `CHG-0xx` → migración previa de datos (si aplica, antes de Fase 1).
- `CHG-1xx` → Fase 1 (fundamentos).
- `CHG-2xx` → Fase 2 (convocatoria piloto).
- `CHG-3xx` → Fase 3 (legalización y pagos).
- `CHG-4xx` → Fase 4 (seguimiento y cierre).
- `CHG-5xx` → Fase 5 (gobernanza, transparencia y mejoras).

---

## 4. Fase 0 — Infraestructura

**Objetivo**: dejar la plataforma **desplegable, observable, segura y
reproducible** en `dev`, `staging` y `prod`, antes de escribir la
primera línea de código de aplicación. Esta fase no entrega valor de
negocio directo, pero sin ella las fases siguientes serían
insostenibles.

> **Política de entorno de desarrollo (dev local)**:
>
> - **La aplicación Django corre en un entorno virtual Python local**
>   (`python -m venv .venv`) con `runserver` (o `django-dev`) para
>   tener **hot reload nativo** (recarga automática de código Python
>   y de templates al guardar, sin reiniciar contenedor).
> - **Los servicios auxiliares** (Postgres, Redis, MinIO) corren en
>   contenedores Docker vía `docker compose up postgres redis minio`
>   (sin web ni worker). Esto evita instalar y versionar servicios
>   nativamente.
> - **Docker se usa para CI, staging y prod** mediante un `Dockerfile`
>   multi-stage. La imagen de la app es la misma que se ejecuta en
>   todos los entornos no-locales.

### 4.1 Capacidades de Infraestructura y Cambios

| ID        | Cambio                          | Título                                                              |
| --------- | ------------------------------- | ------------------------------------------------------------------- |
| INF-001   | `INF-001-repo-bootstrap`        | Estructura del repo, .gitignore, .editorconfig, pre-commit hooks, CODEOWNERS |
| INF-002   | `INF-002-local-dev-env`         | Entorno virtual Python local con hot reload nativo (`runserver`/`django-dev`); servicios auxiliares (Postgres, Redis, MinIO) en `docker-compose.yml` |
| INF-003   | `INF-003-cicd`                  | GitHub Actions: lint (ruff/black/isort), tests, build de imagen Docker, despliegue a staging/prod |
| INF-004   | `INF-004-environments`          | Definición de entornos `dev`/`staging`/`prod`, archivo `.env.example` por entorno, configuración 12-factor |
| INF-005   | `INF-005-secrets`               | Gestión de secrets: variables de entorno, vault/secret manager, rotación, cero secrets en repo |
| INF-006   | `INF-006-observability`         | Logging estructurado (JSON), Sentry, Prometheus, Grafana, health checks (`/healthz`, `/readyz`) |
| INF-007   | `INF-007-postgres-prod`         | PostgreSQL de producción: tuning, connection pooling (PgBouncer), backups automatizados, monitoreo de queries |
| INF-008   | `INF-008-storage-prod`          | Storage S3-compatible de producción: bucket de anexos, versionado, cifrado en reposo, ciclo de vida |
| INF-009   | `INF-009-email-transactional`   | Proveedor de email transaccional, plantillas, retry, rate limiting, dominio verificado (DKIM/SPF/DMARC) |
| INF-010   | `INF-010-security-headers`      | HTTPS/TLS obligatorio, headers de seguridad, rate limiting, WAF, CORS, CSP |
| INF-011   | `INF-011-disaster-recovery`     | Plan de DR, RTO/RPO definidos, backups verificados, procedimiento de restore documentado y probado |
| INF-012   | `INF-012-runbooks`              | Runbooks operacionales: deploy, rollback, incidentes, on-call, procedimientos de escalamiento |
| INF-013   | `INF-013-iac`                   | Infraestructura como código (Terraform o equivalente): red, balanceador, base de datos, storage, IAM |
| INF-014   | `INF-014-migrations-strategy`   | Estrategia de migraciones de BD, zero-downtime deploys, migraciones reversibles, expands/contracts |
| INF-015   | `INF-015-monitoring-alerts`     | Alertas operacionales: capacidad, error rate, latencia, jobs Celery, backups, expiración de certificados |
| INF-016   | `INF-016-perf-baseline`         | Línea base de rendimiento y capacidad: smoke tests, pruebas de carga de la convocatoria piloto |

### 4.2 Entregables verificables

- [ ] Un nuevo desarrollador puede clonar el repo, crear el venv
      (`python -m venv .venv`), instalar dependencias, levantar los
      servicios auxiliares con `docker compose up postgres redis
      minio` y arrancar Django con `python manage.py runserver`
      (o `django-dev`) con hot reload nativo, todo en menos de 30
      minutos y sin pasos manuales adicionales.
- [ ] El `runserver` (o `django-dev`) recarga automáticamente el
      código Python y los templates al guardar, sin reinicio manual.
- [ ] Pre-commit hooks ejecutan ruff, black, isort y secretos.
- [ ] GitHub Actions corre lint + tests + build de imagen Docker
      en cada PR y bloquea merge si fallan.
- [ ] Existen tres entornos diferenciados: `dev` (local),
      `staging` y `prod`, con sus archivos `.env.example` y
      secretos fuera del repo.
- [ ] Los logs son JSON estructurados con request-id y se
      correlacionan entre Django, Celery y Postgres.
- [ ] Sentry captura excepciones; Prometheus + Grafana
      exponen métricas de aplicación e infraestructura.
- [ ] Los endpoints `/healthz` y `/readyz` están operativos y
      diferencian liveness vs readiness.
- [ ] PostgreSQL cuenta con backups automatizados (diarios +
      incrementales) y un procedimiento de restore probado en
      staging.
- [ ] El bucket de anexos tiene versionado, cifrado y política
      de ciclo de vida.
- [ ] El dominio de email está verificado (DKIM/SPF/DMARC) y
      los correos transaccionales salen firmados.
- [ ] HTTPS es obligatorio en todos los entornos no-locales.
- [ ] Rate limiting y headers de seguridad activos en
      `staging` y `prod`.
- [ ] RTO y RPO están documentados y firmados por la
      Secretaría de Educación.
- [ ] Runbooks versionados en el repo (`docs/runbooks/`) para:
      deploy, rollback, incidente de BD, incidente de email,
      incidente de storage.
- [ ] Toda la infraestructura productiva está descrita como
      código (Terraform o equivalente) y es reproducible desde
      cero.

### 4.3 Criterio de salida

> Un nuevo integrante del equipo puede, en menos de 30 minutos,
> clonar el repo, crear el venv, instalar dependencias, levantar
> los servicios auxiliares con `docker compose`, arrancar Django
> con `runserver` (hot reload nativo), hacer un PR, ver pasar el
> pipeline de CI y, tras aprobación, desplegar a `staging` con un
> solo comando (la app corre ya como imagen Docker en
> `staging`/`prod`). Toda la infraestructura de `staging` y `prod`
> es reproducible desde código y es observable.

---

## 5. Fase 1 — Fundamentos de Aplicación

**Objetivo**: dejar lista la plataforma base para soportar
cualquier capacidad posterior. Incluye cumplimiento normativo
desde el día 1 (Ley 1581/2012, CPACA, auditoría).

### 5.1 Capacidades y Cambios

| CAP   | Cambio                  | Título                                              | Apps              |
| ----- | ----------------------- | --------------------------------------------------- | ----------------- |
| 001   | `CHG-101-auth-rbac`     | Autenticación, roles y permisos granulares          | `apps/accounts/`  |
| 022   | `CHG-102-audit`         | Bitácora inmutable con hash chain                   | `apps/audit/`     |
| 023   | `CHG-103-catalogs`      | Catálogos paramétricos del dominio                  | `apps/core/`      |
| 024   | `CHG-104-convocatory-config` | Modelo de configuración de convocatoria (Receta) | `apps/convocatories/`, `apps/core/` |
| 025   | `CHG-105-habeas-data`   | Habeas data y consentimientos (Ley 1581)           | `apps/accounts/`  |
| 019   | `CHG-106-notifications` | Infraestructura base de notificaciones              | `apps/accounts/`  |

### 5.2 Entregables verificables

- [ ] Un usuario puede registrarse, autenticarse y asumir un rol
      interno (Coordinación Técnica, CT, Junta, etc.).
- [ ] Toda acción sobre cualquier modelo queda registrada en la
      bitácora con hash chain.
- [ ] Los catálogos (estrato, SISBÉN, etnia, municipio_isla,
      nivel_formación, modalidad, tipo IES, tipo documento, etc.)
      son administrables vía admin.
- [ ] Existe un modelo `ConfiguracionConvocatoria` con JSON
      validado para soportar los criterios de la convocatoria de
      ejemplo (50/30/20) sin código nuevo.
- [ ] El sistema captura consentimientos y soporta solicitudes de
      consulta, rectificación, actualización y supresión.
- [ ] La infraestructura de notificaciones (email + registro en
      bandeja) está operativa.

### 5.3 Criterio de salida

> Se puede crear un usuario, asignarle un rol, ejecutar una
> acción cualquiera, ver la auditoría con hash válido, y
> configurar programáticamente una convocatoria nueva con sus
> reglas.

---

## 6. Fase 2 — Convocatoria Piloto

**Objetivo**: ejecutar la **Convocatoria Cerrada "Reconocimiento a
la Excelencia" 2026-1** completa, sin papel, hasta la publicación
del listado definitivo.

### 6.1 Capacidades y Cambios

| CAP   | Cambio                          | Título                                       | Apps                       |
| ----- | ------------------------------- | -------------------------------------------- | -------------------------- |
| 002   | `CHG-201-convocatory-engine`    | Crear, configurar, publicar y cerrar convocatorias (ciclo de estados) | `apps/convocatories/` |
| 003   | `CHG-202-applicator-fui`        | Wizard FUI digital + carga de anexos + radicado | `apps/applications/`    |
| 004   | `CHG-203-requirements-check`    | Validación de requisitos mínimos + subsanaciones | `apps/applications/`    |
| 005   | `CHG-204-scoring`               | Motor de scoring configurable (50/30/20) + ranking por municipio + regla Providencia Isla | `apps/scoring/` |
| 006   | `CHG-205-claims`                | Reclamaciones (1ª instancia ante la Junta)   | `apps/claims/`             |
| 007   | `CHG-206-appeals`               | Apelaciones (2ª instancia ante Oficina Jurídica) | `apps/claims/`          |
| 008   | `CHG-207-definitive-results`    | Resultados definitivos + acto administrativo + corrección de errores formales (Art. 45 CPACA) | `apps/convocatories/`, `apps/governance/` |

### 6.2 Entregables verificables

- [ ] Una convocatoria se crea, configura y publica siguiendo el
      cronograma de la convocatoria de referencia.
- [ ] Un aspirante puede registrarse, diligenciar el FUI digital,
      cargar anexos, firmar electrónicamente y obtener radicado.
- [ ] La Coordinación Técnica valida cada uno de los 7 requisitos
      mínimos (verificación manual contra SNIES/SISBÉN/OCCRE,
      registrada como evidencia en la plataforma).
- [ ] El motor de scoring aplica los criterios 50/30/20, maneja
      empates y produce el ranking por municipio (incluida la regla
      de excepción de Providencia Isla).
- [ ] Un aspirante puede presentar reclamación; la Junta la
      resuelve y notifica.
- [ ] Un aspirante puede apelar; la Oficina Jurídica resuelve.
- [ ] La Junta aprueba el listado definitivo y se emite el acto
      administrativo con su consecutivo.
- [ ] Un error formal puede corregirse vía un nuevo acto
      modificatorio (CPACA Art. 45).

### 6.3 Criterio de salida

> La convocatoria de Reconocimiento a la Excelencia 2026-1 puede
> correrse **de extremo a extremo en producción**, con el listado
> definitivo publicado en el portal y los actos administrativos
> firmados y notificados.

---

## 7. Fase 3 — Legalización y Pagos

**Objetivo**: cerrar el ciclo financiero inicial: legalización del
crédito (pagaré, carta de instrucciones, contrato) y autorización
de los primeros desembolsos a IES o a beneficiarios, con
conciliación manual con Tesorería.

### 7.1 Capacidades y Cambios

| CAP   | Cambio                          | Título                                       | Apps                       |
| ----- | ------------------------------- | -------------------------------------------- | -------------------------- |
| 029   | `CHG-301-e-signature`           | Servicio abstracto de firma electrónica + hash SHA-256 | `apps/legalization/` |
| 009   | `CHG-302-legalization`          | Legalización: pagaré, carta de instrucciones, contrato | `apps/legalization/` |
| 010   | `CHG-303-disbursement`          | Autorización de pago (Pres. JA + Sec. Educación) + orden radicada en Tesorería + vista de conciliación manual | `apps/treasury/` |
| 015   | `CHG-304-termination-causals`   | Causales de terminación del convenio y de desembolsos (Art. 14 y 15 Decreto 0372/2025) | `apps/legalization/`, `apps/condonation/` |

### 7.2 Entregables verificables

- [ ] Un beneficiario puede firmar electrónicamente pagaré, carta
      de instrucciones y contrato; los documentos se almacenan con
      hash SHA-256.
- [ ] El Presidente de la JA y el Secretario de Educación firman
      la autorización de pago, y la orden se radica en Tesorería
      con los 4 adjuntos normativos (Art. 2 Decreto 0072/2026).
- [ ] La Tesorería puede marcar una orden como pagada y adjuntar
      el comprobante desde una vista de conciliación manual.
- [ ] El sistema respeta el plazo de 5 días hábiles de Tesorería
      y emite alertas si se vence.
- [ ] Las causales de terminación del convenio y de desembolsos
      están modeladas y operativas.

### 7.3 Criterio de salida

> Un beneficiario legaliza su crédito, recibe su primer desembolso
> y el pago queda conciliado contra el comprobante de Tesorería.

---

## 8. Fase 4 — Seguimiento y Cierre

**Objetivo**: operar el ciclo de vida del beneficiario hasta su
cierre: seguimiento académico, acompañamiento psicosocial,
condonación total/parcial o inicio de cobro.

### 8.1 Capacidades y Cambios

| CAP   | Cambio                          | Título                                       | Apps                       |
| ----- | ------------------------------- | -------------------------------------------- | -------------------------- |
| 011   | `CHG-401-academic-tracking`     | Carga de notas, validación de promedio 3.5, alertas tempranas | `apps/academic_tracking/` |
| 012   | `CHG-402-psychosocial`          | Acompañamiento en 3 momentos (selección, durante, post), red de apoyo, consentimientos | `apps/psychosocial/` |
| 013   | `CHG-403-condonation-partial`   | Incentivos y condonación parcial por promedio | `apps/condonation/`        |
| 014   | `CHG-404-condonation-total`     | Condonación total al graduarse (Art. 16 Decreto 0372/2025) + retorno de 1 año | `apps/condonation/` |
| 016   | `CHG-405-sanctions`             | Sanciones, reintegros con IPC, exoneraciones (30 días), fallecimiento (cesa deuda) | `apps/condonation/` |
| 026   | `CHG-406-special-cases`         | Manejo de casos especiales y fuerza mayor    | `apps/applications/`, `apps/condonation/` |

### 8.2 Entregables verificables

- [ ] Un beneficiario carga su certificado de notas por semestre.
- [ ] El sistema alerta cuando el promedio cae por debajo de 3.5
      o cuando faltan 30 días para la fecha de carga.
- [ ] Se registran intervenciones psicosociales con consentimiento
      expreso.
- [ ] Al graduarse, el beneficiario solicita condonación y la
      Junta la aprueba, previa verificación de promedio y plazos
      máximos por nivel.
- [ ] Un caso de sanción se calcula correctamente con
      actualización por IPC, y la solicitud de exoneración se
      resuelve en 30 días calendario.
- [ ] El fallecimiento del beneficiario cesa la deuda
      automáticamente.

### 8.3 Criterio de salida

> Un beneficiario graduado obtiene su condonación total, o un
> caso de incumplimiento se gestiona hasta el reintegro o la
> exoneración correspondiente.

---

## 9. Fase 5 — Gobernanza, Transparencia y Mejoras

**Objetivo**: completar el ciclo de gobernanza, transparencia y
mejora continua.

### 9.1 Capacidades y Cambios

| CAP   | Cambio                          | Título                                       | Apps                       |
| ----- | ------------------------------- | -------------------------------------------- | -------------------------- |
| 017   | `CHG-501-sessions`              | Sesiones de Junta y CT: orden del día, quórum, votaciones, actas firmadas, conflict-of-interest | `apps/governance/` |
| 018   | `CHG-502-coi`                   | Conflictos de interés (declaración, aprobación del impedimento) | `apps/governance/` |
| 020   | `CHG-503-reports`               | Informes trimestrales y anuales de gestión    | `apps/reporting/`          |
| 021   | `CHG-504-transparency`          | Portal de transparencia / datos abiertos (agregados, sin PII) | `apps/reporting/` |
| 028   | `CHG-505-external-audit`        | Exportación a entes de control (CSV/JSONL sellados) | `apps/audit/`, `apps/reporting/` |
| 027   | `CHG-506-impact`                | Estudio de impacto bianual (Art. 20.f Manual Operativo) | `apps/reporting/` |
| 030   | `CHG-507-multilang`             | i18n español/inglés/creole                    | `apps/accounts/`          |

### 9.2 Entregables verificables

- [ ] Una sesión de Junta se crea, sesiona con quórum, vota cada
      punto, levanta acta firmada y archiva el documento.
- [ ] Un miembro declara conflicto de interés y su voto se
      excluye automáticamente de la decisión.
- [ ] Se generan los informes trimestrales y anuales con KPIs
      normativos.
- [ ] El portal de transparencia publica estadísticas agregadas
      (sin datos personales).
- [ ] Un ente de control puede descargar un paquete de datos
      sellado y firmado.
- [ ] La plataforma soporta múltiples idiomas.

### 9.3 Criterio de salida

> La plataforma opera el ciclo completo de gobernanza interna
> (Junta, CT) y satisface los requerimientos de transparencia,
> auditoría externa y multidioma.

---

## 10. Mapa de Dependencias entre Capacidades

```
        ┌──────────────────────┐
        │ FASE 0: INFRA        │
        │ (INF-001..016)       │
        └──────────┬───────────┘
                   ▼
        ┌──────────────────────┐
        │ FASE 1: FUNDAMENTOS  │
        │ CAP-001/019/022/023/ │
        │ 024/025              │
        └──────────┬───────────┘
                   ▼
   CAP-001 ─► CAP-002 ─► CAP-003 ─► CAP-004 ─► CAP-005
        │            │                ▲
   CAP-022 ─┤        │                │
   CAP-023 ─┼►CAP-024┘                │
   CAP-025 ─┤                          │
   CAP-019 ─┤                          │
        │                              │
        └► CAP-006 ─► CAP-007 ─► CAP-008
                                         │
                                         ▼
                                  CAP-009 (legalización)
                                         │
                                         ▼
                            CAP-029 (firma electrónica)
                                         │
                                         ▼
                                  CAP-010 (desembolsos)
                                         │
                                         ▼
                                  CAP-011 (seg. académico)
                                         │
                          ┌──────────────┴──────────────┐
                          ▼                             ▼
                   CAP-012 (psicosocial)     CAP-013/014 (condonación)
                                                     │
                                                     ▼
                                              CAP-016 (sanciones)
                                                     │
                                                     ▼
                                              CAP-026 (casos esp.)

CAP-017/018 (gobernanza) y CAP-020/021/028 (transparencia/auditoría)
  son transversales: pueden avanzar en paralelo a partir de Fase 1.
```

> Toda capacidad que involucre estados o pagos depende de
> `CAP-001`, `CAP-022` y `CAP-023`. Toda capacidad que registre
> consentimiento depende de `CAP-025`. Toda capacidad depende, en
> última instancia, de la Fase 0 (infraestructura).

---

## 11. Capacidades por Fase (Resumen)

| Fase | Capacidades                                                              | Cambios         |
| ---- | ------------------------------------------------------------------------ | --------------- |
| 0    | INF-001 a INF-016 (16 specs de infraestructura)                          | INF-001 a 016   |
| 1    | CAP-001, 019, 022, 023, 024, 025                                         | CHG-101 a 106   |
| 2    | CAP-002, 003, 004, 005, 006, 007, 008                                   | CHG-201 a 207   |
| 3    | CAP-009, 010, 015, 029                                                   | CHG-301 a 304   |
| 4    | CAP-011, 012, 013, 014, 016, 026                                         | CHG-401 a 406   |
| 5    | CAP-017, 018, 020, 021, 027, 028, 030                                    | CHG-501 a 507   |

**Total**: 30 capacidades de aplicación + 16 de infraestructura =
**46 specs** entregadas a través de **47 cambios** OpenSpec.

---

## 12. Riesgos Globales y Mitigaciones

| #  | Riesgo                                                                  | Mitigación                                                          |
| -- | ----------------------------------------------------------------------- | ------------------------------------------------------------------- |
| R1 | Cambios regulatorios durante la implementación (CPACA, Habeas Data).   | OpenSpec permite actualizar specs sin redeploy completo.            |
| R2 | Adulteración de documentos o suplantación.                              | Firma electrónica + hash + verificación contra autoridad competente. |
| R3 | Sobrecarga de la Coordinación Técnica en momentos pico.                 | Batch processing, UI con asistente, plantillas prediseñadas.        |
| R4 | Falla de procesos bancarios externos.                                   | Reintento manual desde Tesorería; transacciones idempotentes.       |
| R5 | Resistencia al cambio de usuarios institucionales.                       | Plan de cambio + capacitación + manuales.                          |
| R6 | Pérdida de trazabilidad por mal uso.                                    | Bitácora inmutable desde Fase 1 + alertas de comportamiento.       |
| R7 | Filtración de datos personales.                                          | Mínimo privilegio, cifrado, DLP, tests de seguridad periódicos.     |
| R8 | Migración incompleta desde el proceso actual.                            | Plan de migración como change previo a Fase 2 (`CHG-099-migration`). |
| R9 | Captura de datos en zonas sin conectividad.                              | Radicación presencial conservada como opción.                       |
| R10 | Indisponibilidad de infraestructura (DB, storage, email).                | Runbooks de incidente, RTO/RPO definidos, monitoreo con alertas, redundancia. |
| R11 | Pérdida de datos por falla de backups.                                   | Backups verificados periódicamente + DR probado en staging.         |
| R12 | Exposición de secrets en el repo.                                        | Pre-commit hooks + secret scanning en CI + uso de secret manager.  |

> **Nota sobre R8 (migración)**: si se requiere migrar padrones,
> FUI físicos escaneados, resoluciones previas y el listado de
> la convocatoria 001-2025, esto debe hacerse como un change
> previo a la Fase 2 (`CHG-099-migration`), respetando la regla
> de no incluir datos personales en el repo (los datos se
> cargan en la base transaccional, no en el repo de código).

---

## 13. Criterios Globales de Aceptación del Proyecto

El proyecto se considera aceptado cuando se cumplen **todos**:

- [ ] **Cumplimiento normativo**: las reglas del Decreto 0372/2025,
      la Ordenanza 007/2025 y el Manual Operativo están modeladas
      y probadas.
- [ ] **Caso de referencia ejecutado**: la Convocatoria Cerrada
      "Reconocimiento a la Excelencia" 2026-1 corre end-to-end
      sin papel, desde la publicación hasta el primer desembolso.
- [ ] **Trazabilidad total**: toda acción de cualquier actor está
      en la bitácora con hash válido; la Oficina de Control
      Interno puede auditarla.
- [ ] **Habeas data operativo**: el titular puede consultar,
      rectificar, actualizar y suprimir sus datos.
- [ ] **Concurrencia segura**: dos roles distintos pueden operar
      simultáneamente sin romper la segregación de funciones
      (quien autoriza ≠ quien ejecuta ≠ quien audita).
- [ ] **Sin integraciones externas**: no se realizan llamadas a
      SNIES, SISBÉN, OCCRE ni a sistemas bancarios; la
      verificación es manual/externa y la transacción la hace
      Tesorería.
- [ ] **Infraestructura reproducible**: staging y prod pueden
      levantarse desde código (IaC) en menos de un día hábil.
- [ ] **Observabilidad operativa**: logs, métricas, trazas y
      alertas están activos y revisados; los SLOs están definidos.
- [ ] **Disaster recovery probado**: existe un DRP vigente, los
      backups se verifican periódicamente y el restore se ha
      probado en staging.
- [ ] **Seguridad validada**: TLS activo, headers de seguridad
      aplicados, secret scanning, rate limiting y WAF en
      `staging` y `prod`.
- [ ] **Cobertura de pruebas**: ≥ 80% en módulos críticos
      (`scoring/`, `legalization/`, `treasury/`, `condonation/`,
      `audit/`).
- [ ] **Portal de transparencia público**: estadísticas agregadas
      sin PII, actualizadas trimestralmente.

---

## 14. Convenciones de Nombrado para Cambios

- **Prefijo**:
  - `INF-NNN` para infraestructura (Fase 0).
  - `CHG-NNN` para aplicación/dominio (Fases 1–5).
  - `CHG-099` reservado para el change de migración de datos
    previo a Fase 2, si aplica.
- **Slug**: kebab-case, max 50 caracteres, en inglés.
- **Numeración por fase**:
  - `INF-0xx` (Fase 0), `CHG-1xx` (Fase 1), `CHG-2xx` (Fase 2),
    `CHG-3xx` (Fase 3), `CHG-4xx` (Fase 4), `CHG-5xx` (Fase 5).
- **ID libre** entre cambios de la misma fase: 001, 002, 003...
- Cada change referencia los `CAP-NNN` o `INF-NNN` que materializa
  en su `proposal.md`.

> Cualquier excepción a esta convención debe justificarse en el
> `proposal.md` del change correspondiente.
