# CHG-208 — Cierre del piloto Fase 2 (workflow de actos + e2e tests)

## Contexto

`roadmap.md §6.2` declara la Fase 2 (Convocatoria Piloto) lista cuando
los siete deliverables verificables están cumplidos. Cinco están
marcados ✅ (CHG-201..204) y dos aún no (CHG-205..207).

La auditoría focalizada sobre `apps/claims/` y `apps/governance/`
revela que **CHG-205 y CHG-206 están sustancialmente implementados**
en código pero les faltan tests end-to-end que prueben el flujo
completo. **CHG-207 está implementado a nivel de modelos, vistas y
servicios, pero le faltan dos vistas críticas** en su workflow:

- `ActoSignView` (BORRADOR → FIRMADO). Sin esta vista, la transición
  que valida `ActoPublishView` (`if acto.estado != FIRMADO`) es
  inalcanzable: el workflow del acto se rompe en BORRADOR y nunca
  llega a PUBLICADO.
- `ActoModificatorioCreateView` (CPACA Art. 45). El modelo
  `ActoAdministrativo` ya soporta el tipo `modificatorio` y la FK
  `acto_original` (modelo `apps/governance/models.py:90-96`), pero
  no hay vista ni URL que cree un acto modificatorio enlazado al
  original. La corrección de errores formales prometida en
  `roadmap.md §6.2` no es operable.

Adicionalmente, ningún change tiene tests end-to-end del flujo
"inscripción → scoring → reclamación → apelación → resultado
definitivo → publicación". El piloto corre en producción sin que
haya un test que verifique el viaje completo del usuario.

## Capacidades afectadas

- **CAP-006** (Reclamaciones, 1ª instancia ante la Junta) —
  `project.md §8`. Materializa CHG-205.
- **CAP-007** (Apelaciones, 2ª instancia ante la Oficina Jurídica) —
  `project.md §8`. Materializa CHG-206.
- **CAP-008** (Resultados definitivos + acto administrativo) —
  `project.md §8`. Materializa CHG-207.

## Reglas de negocio afectadas

- `AGENTS.md` §6 regla 5 (no saltarse pruebas en transiciones de
  estado ni en generación de actos administrativos).
- `AGENTS.md` §6 regla 6 (lógica de workflow en `services/`, no en
  vistas — la máquina de estados BORRADOR→FIRMADO→PUBLICADO
  debe residir en `apps.governance.domain.transitions`).
- `roadmap.md §6.2` (entregables verificables de Fase 2).
- CPACA Art. 45 (corrección de errores formales vía acto
  modificatorio).

## Cambios propuestos

### Delta en `specs/governance/spec.md`

#### MODIFIED — § Workflow de actos administrativos

`ActoAdministrativo` SHALL transicionar por los estados
`BORRADOR → FIRMADO → PUBLICADO` exclusivamente a través de vistas
dedicadas (`ActoSignView` para BORRADOR→FIRMADO,
`ActoPublishView` para FIRMADO→PUBLICADO). **Una transición
directa BORRADOR→PUBLICADO SHALL ser rechazada.** El estado se
persiste de forma atómica (`transaction.atomic` +
`select_for_update` sobre la fila) para evitar firmas concurrentes.

#### ADDED — § Acto modificatorio (CPACA Art. 45)

Un `ActoAdministrativo` de tipo `MODIFICATORIO` SHALL referenciar
un acto original via FK `acto_original`. SHALL heredar el
`convocatoria` del original. No SHALL poder referenciar otro
modificatorio (la cadena es de un solo nivel: original →
modificatorio). La creación de un modificatorio SHALL requeririr
el rol `R-JUNTA`.

### Delta en `specs/claims/spec.md`

#### MODIFIED — § Lifecycle de Reclamación (CHG-205)

El ciclo de vida SHALL cubrir:
`PRESENTADA → EN_REVISION → RESUELTA | DESESTIMADA` con
transiciones registradas en `ReclamacionHistorial`. Una
`RESUELTA` favorable SHALL habilitar la creación de una Apelación
(rol `R-ASPIRANTE`). Una `DESESTIMADA` SHALL agotar la vía
gubernativa (CPACA).

#### MODIFIED — § Lifecycle de Apelación (CHG-206)

El ciclo SHALL ser:
`INICIADA → EN_ANALISIS → CONFIRMADA | REVOCADA`. Una
`CONFIRMADA` ratifica la `RESUELTA` original; una `REVOCADA`
invalida la decisión de primera instancia y el expediente vuelve
a la Junta con orden de re-decisión.

## Cambios concretos

1. **`apps/governance/views.py`**: agregar `ActoSignView` que
   valida `estado=BORRADOR`, persiste `estado=FIRMADO` y registra
   `firmantes` y `fecha_firma`. Usar `transaction.atomic` +
   `select_for_update()`.

2. **`apps/governance/views.py`**: agregar
   `ActoModificatorioCreateView` (CBV) que crea un
   `ActoAdministrativo` con `tipo=MODIFICATORIO`,
   `acto_original=<pk>`, `convocatoria=<del original>`,
   `numero=generar_numero_acto("modificatorio")`. Sólo rol
   `R-JUNTA`.

3. **`apps/governance/urls.py`**: agregar `path("actos/<uuid:pk>/firmar/",
   ActoSignView.as_view(), name="acto_sign")` y
   `path("actos/<uuid:pk>/modificatorio/", ActoModificatorioCreateView.as_view(),
   name="acto_modificatorio_create")`.

4. **`apps/governance/domain/transitions.py`**: agregar
   `firmar_acto(acto, firmantes)` y `crear_modificatorio(original,
   **campos_override)` que viven en `domain/` (no en `views/`).
   Las vistas solo orquestan.

5. **`apps/governance/tests/test_workflow.py`** (nuevo): probar
   transiciones válidas (`BORRADOR→FIRMADO→PUBLICADO`) y
   transiciones inválidas (`BORRADOR→PUBLICADO` debe rechazar;
   doble firma concurrente debe serializarse via
   `select_for_update`).

6. **`apps/governance/tests/test_modificatorio.py`** (nuevo):
   crear un acto original, crear un modificatorio que lo
   referencia, verificar que `acto_original` y `convocatoria`
   se heredan, verificar que un modificatorio NO puede
   referenciar otro modificatorio.

7. **`apps/claims/tests/test_reclamacion_flow.py`** (nuevo):
   e2e del flujo de reclamación: crear solicitud → presentar
   reclamación → transición a `EN_REVISION` → resolución
   favorable → habilitación de apelación.

8. **`apps/claims/tests/test_apelacion_flow.py`** (nuevo): e2e
   del flujo de apelación: tras reclamación resuelta favorable →
   crear apelación → análisis → confirmación.

9. **`apps/governance/tests/test_pilot_e2e.py`** (nuevo): un solo
   test que ejecuta el flujo completo:
   - convocatoria publicada
   - scoring produce ranking
   - reclamación → apelación → resultado definitivo
   - acto firmado y publicado
   - listado definitivo visible en portal público

## Criterios de aceptación

- [ ] `ActoSignView` existe, valida `estado=BORRADOR`, transiciona a
      `FIRMADO` y persiste `firmantes` + `fecha_firma`.
- [ ] `ActoPublishView` rechaza intento de publicación de acto en
      `BORRADOR` (test explícito).
- [ ] `ActoModificatorioCreateView` crea acto con FK al original,
      hereda `convocatoria`, rechaza intento de referenciar otro
      modificatorio.
- [ ] Test concurrente: dos hilos intentando firmar el mismo acto
      → uno gana, el otro recibe `ConcurrencyError` o `ValueError`
      limpio.
- [ ] `pytest apps/claims/tests/test_reclamacion_flow.py` corre limpio.
- [ ] `pytest apps/claims/tests/test_apelacion_flow.py` corre limpio.
- [ ] `pytest apps/governance/tests/test_workflow.py` corre limpio.
- [ ] `pytest apps/governance/tests/test_modificatorio.py` corre limpio.
- [ ] `pytest apps/governance/tests/test_pilot_e2e.py` corre limpio.
- [ ] Spec deltas aplicados en
      `openspec/changes/CHG-208-pilot-completion/specs/{governance,claims}/spec.md`.

## Pruebas

- Unitarias:
  - `apps/governance/tests/test_workflow.py` — state machine + atomicidad
  - `apps/governance/tests/test_modificatorio.py` — CPACA Art. 45
- Integración:
  - `apps/claims/tests/test_reclamacion_flow.py`
  - `apps/claims/tests/test_apelacion_flow.py`
- End-to-end:
  - `apps/governance/tests/test_pilot_e2e.py` (cubre convocatoria →
    piloto completo)

## Riesgos y Fuera del alcance

- **Riesgo**: el piloto real corre en producción con datos reales
  mientras este change está en desarrollo. Mitigación: las nuevas
  vistas son ADITIVAS — no modifican el flujo actual hasta que
  la URL esté desplegada.
- **Riesgo**: `select_for_update` en SQLite no bloquea a nivel de fila
  (usa DB-level lock). El test concurrente debe correr contra
  PostgreSQL para validar el comportamiento. Mitigación: marcar
  el test concurrente con `@pytest.mark.skipif` para SQLite.
- **Fuera del alcance**:
  - No se rediseña el modelo `ActoAdministrativo`.
  - No se reemplaza WeasyPrint por otra librería de PDF.
  - No se agrega workflow de Junta multi-firma (cada firmante
    puede firmar; queda para `CHG-501-sessions`).
  - No se agrega el portal público con PII; `ListadoPublicoView`
    ya excluye PII correctamente.

## Referencias

- `roadmap.md §6.2` (entregables verificables de Fase 2)
- `roadmap.md §10` (dependencias CAP-006 → CAP-007 → CAP-008)
- `apps/governance/models.py:8-150` (modelos ya implementados)
- `apps/governance/views.py` (vistas ya implementadas)
- `apps/claims/views.py:28-540` (vistas ya implementadas)
- CPACA Art. 45 (corrección de actos administrativos)
