# Stubs eliminados — CHG-806

> Documento vivo. Referencia:
> `openspec/changes/CHG-806-stub-cleanup/proposal.md`,
> `docs/audits/extended-audit.md §6 + §8.3 AUD-024/AUD-025`.

## Apps removidas del árbol en CHG-806

| App removida | CAP-NNN | Roadmap § | Change OpenSpec que la reintroducirá |
|--------------|---------|-----------|--------------------------------------|
| `apps/reporting/`     | CAP-020 (Informes trimestrales y anuales), CAP-021 (Portal de transparencia), CAP-027 (Estudio de impacto bianual), CAP-028 (Exportación a entes de control) | `roadmap.md §9.1` (Fase 5) | Por definir al abrir Fase 5. Candidatos: `CHG-503-reports`, `CHG-504-transparency`, `CHG-505-external-audit`, `CHG-506-impact`. |
| `apps/psychosocial/`  | CAP-012 (Acompañamiento psicosocial, 3 momentos) | `roadmap.md §8.1` (Fase 4) | `CHG-402-psychosocial` (aún no abierto). |

Las dos apps estaban registradas en `INSTALLED_APPS` pero sólo
`apps.py` tenía contenido (7 líneas declarando el `AppConfig`). El
resto eran archivos de 0 bytes. Mantener el código cargado sin
funcionalidad generaba tres riesgos documentados en el proposal:
imports silenciosos fallidos, `ModuleNotFoundError` confusos al
intentar importar submódulos, y deuda de trazabilidad (AGENTS.md §6
regla 9).

## Placeholder agregado

| Path | CAP-NNN | Estado |
|------|---------|--------|
| `apps/governance/sessions/` (con `__init__.py` + `README.md`) | CAP-017 (Sesiones de Junta) | placeholder — implementación real en `CHG-501-sessions`, Fase 5 |

Este placeholder existe para que un dev futuro reciba un error
explícito al intentar usar el módulo antes de su implementación
aprobada.

## Cómo reintroducir cuando llegue el momento

Cuando se abra el change que reintroduce una de estas apps (p.ej.
`CHG-402-psychosocial`), el flujo correcto es:

1. Abrir `openspec/changes/CHG-402-psychosocial/proposal.md`
   siguiendo la plantilla de AGENTS.md §4.
2. Citar esta nota en el `## Contexto` del proposal
   ("app reintroducida tras limpieza CHG-806").
3. Crear la estructura `apps/psychosocial/` con `apps.py` (que sí
   tiene contenido), `models.py`, `migrations/`, etc.
4. Agregar `"apps.psychosocial"` de vuelta a
   `config/settings.py:INSTALLED_APPS`.
5. Borrar la fila correspondiente de la tabla de arriba.

## Referencias

- `openspec/changes/CHG-806-stub-cleanup/proposal.md` — propuesta
  completa.
- `openspec/changes/CHG-806-stub-cleanup/apply-progress.md` —
  evidencia de cierre.
- `docs/audits/extended-audit.md §6` — hallazgo AUD-024.
- `roadmap.md §8.1` (CAP-012) y `§9.1` (CAP-017/020/021/027/028).
