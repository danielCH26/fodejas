# Tasks — CHG-208 Cierre del piloto Fase 2

> Referencia: `proposal.md`. Plantilla según `AGENTS.md §4`.

## 1. Workflow de actos (governance) — vistas faltantes

- [x] Agregar `ActoSignView` en `apps/governance/views.py`:
  - [x] Recibe POST con `pk` del acto.
  - [x] Valida `estado == BORRADOR`; si no, `HttpResponseBadRequest`.
  - [x] En `transaction.atomic`: `select_for_update().get(pk=pk)`,
        setea `estado=FIRMADO`, `firmantes=<lista del form>`,
        `fecha_firma=timezone.now()`, save.
  - [x] Mensaje de éxito, redirect a `acto_detail`.
- [x] Agregar `ActoModificatorioCreateView` en `apps/governance/views.py`:
  - [x] Recibe GET con `pk` del acto original.
  - [x] GET renderiza form pre-poblado con `acto_original=<pk>`,
        `convocatoria=<original.convocatoria>`.
  - [x] POST valida que `original.tipo != MODIFICATORIO`
        (no se puede crear un modificatorio de un modificatorio).
  - [x] POST crea el acto con
        `numero=generar_numero_acto("modificatorio")`,
        `tipo=MODIFICATORIO`, `acto_original=original`,
        `convocatoria=original.convocatoria`, campos del form.
  - [x] Redirect a `acto_detail` del nuevo acto.

## 2. URLs (governance)

- [x] Agregar en `apps/governance/urls.py`:
  - [x] `path("actos/<uuid:pk>/firmar/", ActoSignView.as_view(), name="acto_sign")`
  - [x] `path("actos/<uuid:pk>/modificatorio/", ActoModificatorioCreateView.as_view(), name="acto_modificatorio_create")`

## 3. Lógica de dominio (governance)

- [x] En `apps/governance/domain/transitions.py` agregar:
  - [x] `firmar_acto(acto_id, firmantes, usuario)` — `transaction.atomic` +
        `select_for_update`, valida estado, retorna `ActoAdministrativo`
        firmado o lanza `ValueError`.
  - [x] `crear_modificatorio(acto_original_id, **campos)` — valida que
        `original.tipo != MODIFICATORIO`, crea el nuevo acto con
        `acto_original=<original>`, `convocatoria=<original.convocatoria>`,
        retorna el nuevo acto.
- [x] Las vistas (`ActoSignView`, `ActoModificatorioCreateView`) deben
      llamar a estas funciones; NO deben manipular `objects.update()` /
      `objects.create()` directamente.

## 4. Tests del workflow

- [x] Crear `apps/governance/tests/test_workflow.py`:
  - [x] `test_sign_transitions_borrador_to_firmado` — crea acto en
        BORRADOR, llama firmar_acto, verifica estado.
  - [x] `test_publish_rejects_borrador` — acto en BORRADOR, intenta
        publicar, debe rechazar.
  - [x] `test_sign_rejects_firmado` — acto ya firmado, intenta firmar
        de nuevo, debe rechazar.
  - [x] `test_concurrent_sign_serializes` — 2 hilos intentan firmar
        el mismo acto, uno gana, el otro lanza `ValueError` o
        `OperationalError`. Marcar con `@pytest.mark.skipif` para
        SQLite (sólo PostgreSQL testea el lock de fila real).

- [x] Crear `apps/governance/tests/test_modificatorio.py`:
  - [x] `test_create_modificatorio_inherits_convocatoria`
  - [x] `test_modificatorio_requires_original_not_modificatorio`
  - [x] `test_modificatorio_number_uses_modificatorio_sequence`

## 5. Tests de flujo Fase 2 (claims)

- [x] Crear `apps/claims/tests/test_reclamacion_flow.py`:
  - [x] `test_reclamacion_presentada_to_resuelta` — crear solicitud,
        presentar reclamación, transicionar a EN_REVISION, resolver
        favorable, verificar ReclamacionHistorial.
  - [x] `test_reclamacion_resuelta_habilita_apelacion` — tras resolver
        favorable, verificar que el flujo de apelación es accesible.

- [x] Crear `apps/claims/tests/test_apelacion_flow.py`:
  - [x] `test_apelacion_iniciada_to_confirmada` — tras reclamación
        resuelta favorable, crear apelación, análisis, confirmar.
  - [x] `test_apelacion_revocada_invalidates_first_instance` — tras
        revocar, verificar que el expediente vuelve a Junta con
        orden de re-decisión.

## 6. Test end-to-end del piloto

- [x] Crear `apps/governance/tests/test_pilot_e2e.py`:
  - [x] `test_full_pilot_flow` — un solo test que:
    - [x] Crea convocatoria (estado PUBLICADA)
    - [x] Crea solicitudes y scoring (mock si necesario)
    - [x] Presenta reclamación → resuelve → apela → confirma
    - [x] Genera listado definitivo con `ListadoDefinitivoCreateView`
    - [x] Verifica que el acto se creó en BORRADOR
    - [x] Firma el acto con `ActoSignView` (vía test client)
    - [x] Publica el acto con `ActoPublishView`
    - [x] Verifica que `ListadoPublicoView` lo muestra
  - [x] `test_pilot_modificatorio_after_publication` — acto modificatorio
        después de publicar.

## 7. Spec deltas

- [x] Crear `openspec/changes/CHG-208-pilot-completion/specs/governance/spec.md`
      con bloques MODIFIED (workflow state machine) y ADDED (acto
      modificatorio CPACA Art. 45).
- [x] Crear `openspec/changes/CHG-208-pilot-completion/specs/claims/spec.md`
      con bloques MODIFIED para los lifecycles de Reclamación y Apelación.

## 8. Verificación final

- [ ] `python -c "import ast; ast.parse(open('apps/governance/views.py').read())"`
- [ ] `python -c "import ast; ast.parse(open('apps/governance/domain/transitions.py').read())"`
- [ ] `python -m pytest apps/governance/tests/test_workflow.py apps/governance/tests/test_modificatorio.py apps/claims/tests/test_reclamacion_flow.py apps/claims/tests/test_apelacion_flow.py apps/governance/tests/test_pilot_e2e.py --no-header -q`
- [ ] `python manage.py check`
- [ ] Ningún test pre-existente se rompe.

## 9. Hand-off

- [ ] Escribir `openspec/changes/CHG-208-pilot-completion/apply-progress.md`
      con resumen, archivos tocados, comandos de verificación y
      resultados.
