# `apps/governance/sessions/` — placeholder para CAP-017

> Paquete intencionalmente vacío. Marcador creado por CHG-806.

## Status

**Placeholder.** Este paquete existe solo para que un dev que intente
`from apps.governance.sessions import X` reciba un `ImportError`
explícito en lugar de un `ModuleNotFoundError` confuso.

## Capability cubierta

**CAP-017** — Sesiones de Junta y CT: orden del día, quórum,
votaciones, actas firmadas, conflict-of-interest.

## Roadmap

`roadmap.md §9.1` — **Fase 5 — Gobernanza, Transparencia y Mejoras**.

La implementación completa de CAP-017 **NO** entra en la piloto. Se
materializará cuando se abra y apruebe el change OpenSpec
`CHG-501-sessions`.

## Estructura mínima esperada (cuando se implemente)

```
apps/governance/sessions/
├── __init__.py
├── README.md             (este archivo)
├── models.py             Sesion, OrdenDelDia, Voto, Quorum, ActaSesion,
│                         ConflictoInteres
├── apps.py               SessionsConfig
├── admin.py              Registro de los modelos en Django admin
├── migrations/
├── services/
│   ├── __init__.py
│   ├── quorum.py         Cálculo de quórum (asistencia + mayorías)
│   └── voting.py         Votaciones nominales /_secretas + registro
├── views/
│   ├── __init__.py
│   └── sesiones.py       CRUD de sesiones + orden del día + votaciones
├── urls.py
└── tests/
    ├── __init__.py
    ├── test_quorum.py    Border cases de quórum (mayorías, ausencias)
    ├── test_voting.py    Votación con COI (CAP-018) excluido
    └── test_sesiones.py  Ciclo completo de una sesión
```

## Restricciones mientras esté como placeholder

- NO agregar `models.py` ni cualquier archivo ejecutable.
- NO modificar este README sin proposal OpenSpec aprobada.
- NO agregar imports en otros módulos que dependan de este paquete.
- Si necesitas la funcionalidad, **abre un nuevo change** (no editar
  este paquete directamente).

## Referencias

- `roadmap.md §9.1` — Fase 5 / CAP-017 / CAP-018.
- `openspec/changes/CHG-806-stub-cleanup/proposal.md` — change que
  creó este placeholder.
- `docs/stubs-removed.md` — nota histórica sobre apps eliminadas
  también por CHG-806.
