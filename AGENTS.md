# AGENTS.md — Guía Operativa para IAs

> Instrucciones operativas para cualquier agente que trabaje en este repo
> bajo la metodología **OpenSpec**. El **qué** del dominio vive en
> `project.md`. El **cómo detallado** vive en `specs/<capability>/spec.md`.
> Las propuestas de cambio se archivan en `changes/<change-id>/`.

## 1. Visión General

Plataforma web **Django 5 + PostgreSQL 16** para digitalizar el ciclo
completo de las convocatorias del **FODEJAS** (Fondo para el Desarrollo
Educativo de los Jóvenes del Archipiélago) de la Secretaría de
Educación Departamental de San Andrés, Providencia y Santa Catalina.

**Sí hace**: publicar convocatorias, recibir postulaciones, validar
requisitos, calcular puntajes, gestionar reclamaciones/apelaciones,
emitir actos administrativos, formalizar créditos, **ordenar** pagos
a Tesorería, hacer seguimiento académico/psicosocial, gestionar
condonaciones, informes y portal de transparencia.

**No hace**:

- **No se integra** con SNIES, SISBÉN ni OCCRE. La verificación es
  **manual/externa** y se registra como evidencia.
- **No se integra** con sistemas bancarios. Tesorería ejecuta el pago
  desde sus sistemas; la plataforma solo **ordena** y concilia.
- **No contiene datos personales** en `project.md`, `AGENTS.md`,
  propuestas, tasks, specs, commits, fixtures ni logs. Los listados
  nominales viven en los sistemas transaccionales con controles PII
  (Ley 1581/2012).

## 2. Convenciones Técnicas

- **Stack**: Django 5, DRF, PostgreSQL 16, Redis+Celery, HTMX,
  WeasyPrint, Docker, GitHub Actions. Storage S3-compatible (MinIO dev).
- **Estilo**: PEP 8, Black (100), Ruff, isort. Docstrings Google.
- **Tests**: `pytest` + `pytest-django` + `factory_boy`.
- **Idiomas**: código en inglés, UI y docs en español.
- **Git**: `main`, `develop`, `feat/<id>-<slug>`, `fix/<id>-<slug>`,
  `chore/<slug>`, `docs/<slug>`. Conventional Commits referenciando
  `CAP-NNN` y/o `CHG-XXX`. Squash merge.
- **PII**: nunca en código, fixtures, commits ni logs. Enmascarar PII
  en logs (helper `apps/core/logging.py`). Retención 20 años para
  expedientes contractuales.

## 3. Estructura OpenSpec

```
openspec/
├── project.md
├── AGENTS.md
├── specs/<capability>/spec.md
└── changes/<change-id>/
    ├── proposal.md   # por qué
    ├── tasks.md      # cómo
    └── specs/.../spec.md   # delta propuesto
```

**Reglas del flujo**:

1. Toda propuesta a una capacidad documentada (`CAP-NNN` del catálogo
   en `project.md` §8) **debe** pasar por `proposal.md` + `tasks.md` +
   delta en `specs/`.
2. No se modifica `project.md` desde un proposal salvo cambio
   estructural al dominio o capacidad nueva.
3. El delta usa bloques `## ADDED / ## MODIFIED / ## REMOVED /
   RENAMED` y declaraciones **SHALL** (neutral a implementación).
4. `proposal.md` cita capacidades (`CAP-NNN`), reglas de negocio
   (`project.md §11.X`) y normativa. **No inventar normativa**.

## 4. Plantilla Mínima de un Change

`proposal.md`:

```markdown
# <Título>
## Contexto
<por qué>
## Capacidades afectadas
- CAP-NNN — <descripción>
## Reglas de negocio afectadas
- project.md §11.X — <descripción>
## Cambios propuestos
<resumen del delta>
## Criterios de aceptación
- [ ] <verificable>
## Pruebas
- <qué se prueba>
## Riesgos y Fuera del alcance
```

`tasks.md`:

```markdown
# Tasks — <Título>
## 1. <Tarea>
- [ ] <subtarea verificable>
## 2. Pruebas
- [ ] unitarias / integración
```

## 5. Mapa Capacidad → App Django

| Capacidad | App |
| --- | --- |
| CAP-001 Auth/Roles | `apps/accounts/` |
| CAP-002 Convocatorias | `apps/convocatories/` |
| CAP-003 Inscripción FUI | `apps/applications/` |
| CAP-004 Validación requisitos | `apps/applications/` |
| CAP-005 Scoring | `apps/scoring/` |
| CAP-006/007 Reclamaciones/Apelaciones | `apps/claims/` |
| CAP-008 Resultados definitivos | `apps/convocatories/` |
| CAP-009 Legalización | `apps/legalization/` |
| CAP-010 Desembolsos | `apps/treasury/` |
| CAP-011 Seg. académico | `apps/academic_tracking/` |
| CAP-012 Acomp. psicosocial | `apps/psychosocial/` |
| CAP-013/014 Condonación | `apps/condonation/` |
| CAP-015/016 Terminación/sanciones | `apps/condonation/` |
| CAP-017/018 Gobernanza | `apps/governance/` |
| CAP-019 Notificaciones | `apps/accounts/` |
| CAP-020/021 Reportes/transparencia | `apps/reporting/` |
| CAP-022 Bitácora auditoría | `apps/audit/` |
| CAP-023/024 Catálogos/config | `apps/core/` |
| CAP-025 Habeas data | `apps/accounts/` |
| CAP-026 Casos especiales | `apps/applications/` |
| CAP-027/028 Impacto/auditoría ext. | `apps/reporting/` |
| CAP-029 Firma electrónica | `apps/legalization/` |
| CAP-030 Multidioma | `apps/accounts/` |

## 6. Reglas de Oro (No Negociables)

1. **No escribir datos personales** en ningún archivo del repo. Usar
   datos sintéticos (`Aspirante Ejemplo`, `1234567890`).
2. **No proponer integraciones externas** (SNIES, SISBÉN, OCCRE,
   bancos). Verificación manual/externa; transacción bancaria en
   Tesorería.
3. **No saltarse OpenSpec**: no modificar `specs/` ni `project.md`
   sin `proposal.md` + `tasks.md` con delta.
4. **No inventar normativa**. Citar siempre
   (e.g. `Ordenanza 007/2025 Art. 5`, `Decreto 0372/2025 Art. 11`).
5. **No saltarse pruebas** en: scoring (CAP-005), transiciones de
   estado, generación de actos administrativos, condonación/sanciones,
   reglas monetarias o de plazos.
6. **No mover lógica de negocio** a vistas o templates. Vive en
   `services/`, `domain/`, `selectors/`.
7. **No inventar plazos**. Plazos normativos (Art. 16 Decreto
   0372/2025): técnico 3a, tecnológico 4a, pregrado 6a, esp./maestría
   2a, doctorado 5a; beneficio 5a/10sem; Tesorería 5 días hábiles;
   exoneraciones 30 días calendario.
8. **No asumir fuera del alcance**: sin microservicios, sin app móvil
   nativa, sin frontend SPA en primera iteración. Roadmap, no
   implementación.
9. **No romper la trazabilidad**: no borrar eventos de auditoría, no
   `git push --force` a `main`/`develop`.
10. **No renombrar `CAP-NNN`** sin proposal.

## 7. Convenciones Internas

- **Estados**: `TextChoices` en el modelo; transiciones explícitas en
  `domain/transitions.py`; cada transición registrada en `audit/`.
- **Reglas de convocatoria**: son **datos**
  (`ConfiguracionConvocatoria` con JSON validado), no código.
- **Bitácora** (CAP-022): append-only con hash chain. Insertar desde
  servicio/contexto, nunca desde la vista.
- **Actos administrativos**: numeración centralizada en
  `apps/governance/`; formato `<prefijo>-<yyyy>-<consecutivo>`.
- **Firma electrónica** (CAP-029): servicio abstracto
  (`signer.py`) con implementaciones intercambiables; siempre
  almacenar hash SHA-256.
- **Pagos**: la plataforma **ordena** y concilia; Tesorería
  **ejecuta** fuera. Vista de conciliación manual donde Tesorería
  marca pagada y adjunta comprobante. **No** integrar con bancos.

## 8. Checklist Pre-Merge

- [ ] Estructura del change según §4 (`proposal.md` + `tasks.md` + delta).
- [ ] Capabilities (`CAP-NNN`) y reglas (`project.md §11.X`) citadas.
- [ ] Delta en `specs/` con bloques `ADDED/MODIFIED/REMOVED/RENAMED` y SHALL.
- [ ] Sin datos personales en ningún archivo.
- [ ] Sin integraciones externas propuestas.
- [ ] Pruebas planeadas para scoring, estados, validaciones críticas.
- [ ] Commits referencian `CHG-XXX` y/o `CAP-NNN`.
- [ ] Rama sigue convención §2.
- [ ] Si hay entidades/estados/dependencias nuevas, justificadas.
