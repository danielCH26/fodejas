# Tasks — CHG-506 Estudio de Impacto (CAP-027)

## 1. Modelo y migraciones

- [ ] 1.1 Añadir `ies_nombre` (CharField 255, blank/null) y
  `municipio_origen` (FK core.MunicipioIsla, on_delete=SET_NULL,
  null/blank) a `Solicitud` en `apps/applications/models.py`;
  normalizar en `save()` con `strip()` + colapso de espacios.
  Generar migración con `makemigrations apps/applications`.

- [ ] 1.2 Añadir `retorno_archipelago` (BooleanField null=True,
  blank=True) a `AcademicRecord` en
  `apps/academic_tracking/models.py`.
  Generar migración con `makemigrations apps/academic_tracking`.

- [ ] 1.3 Crear comando
  `apps/core/management/commands/seed_municipio_isla.py` que haga
  `get_or_create` de los tres municipios del Archipiélago
  (códigos de `wizard_step_1.html:86-88`;
  nombres de `project.md:42`):
  `san_andres` / San Andrés, `providencia` / Providencia y Santa Catalina.
  Idempotente; runnable múltiples veces sin duplicados.

## 2. Backfill

- [ ] 2.1 Crear comando
  `apps/applications/management/commands/backfill_impact_fields.py`:

  - Iterar `Solicitud.objects.iterator(batch_size=500)`.
  - Para cada registro: parsear `datos_academicos.institucion` →
    `strip()` + `re.sub(r' {2,}', ' ', v)`.
  - Para municipio: comparar `datos_personales.municipio` (casefold)
    contra `MunicipioIsla.objects.values_list("codigo", flat=True)`.
  - Match → asignar FK; sin match → null + contador.
  - Escribir solo si el valor destino difiere del actual
    (idempotencia).
  - Bandera `--dry-run`: emite contadores sin transacción.
  - Reportar al final: total procesado, actualizados, sin-match
    municipio, sin institucion.

- [ ] 2.2 Tests del backfill en
  `apps/applications/tests/test_backfill_impact_fields.py`:

  - `test_match_institucion_normaliza_espacios`.
  - `test_no_match_municipio_deja_null`.
  - `test_match_municipio_asigna_fk`.
  - `test_idempotencia_sin_duplicados`.
  - `test_dry_run_no_modifica_bd`.

## 3. Servicio estudio

- [ ] 3.1 Añadir método `ReportingService.estudio_impacto(anio_inicio,
  anio_fin)` en `apps/reporting/services.py`:

  - Validar `1 <= anio_fin - anio_inicio <= 4`; blando para
    estudio bianual = 2 años.
  - Beneficiarios por cohorte/año desde `convocatoria.ano` y
    `AcademicRecord.status`.
  - Tasa graduación y tasa retorno
    (`AcademicRecord.retorno_archipelago=True` / total annotable,
    null excluido).
  - Montos por IES desde `ies_nombre` (sin join a JSON);
    aplicar k=3 en `_k_suppress(items, count_key)` helper:
    celdas <3 → `"Otros (suprimido)"`.
  - Beneficiarios por municipio con k=3 análogo.
  - Desglose por nivel de formación desde
    `datos_academicos.nivel_formacion`.
  - Desglose por convocatoria con montos desde
    `DisbursementAuthorization` join a `LegalizationProcess` → `Solicitud`.
  - Sin PII: ningún nombre, documento, email, teléfono.

- [ ] 3.2 Tests del servicio en
  `apps/reporting/tests/test_estudio_impacto.py`:

  - `test_montos_suman_contra_fixture` (regla monetaria,
    AGENTS.md §6 Regla 5): 3 disbursements fixture → suma verificada.
  - `test_k_suppression_ies_menos_de_3`.
  - `test_k_suppression_municipio_menos_de_3`.
  - `test_rango_invalido_raise_valueerror`.
  - `test_rango_excede_5_raise_valueerror`.
  - `test_tasa_retorno_excluye_null`.

## 4. Endpoints

- [ ] 4.1 Endpoint GET `/api/reporting/estudio-impacto/` en
  `apps/reporting/views.py` con
  `HasAnyRole(REPORT_ROLES + ["R-CT"])`;
  `REPORT_ROLES = ["R-COORD", "R-JUNTA", "R-SECEDU", "R-ADMIN"]`
  (`views.py:14`); se añade `R-CT` por responsabilidad de CT
  (`project.md §6.1.2`).
  Validar `anio_inicio`, `anio_fin`; `400` en params inválidos.
  Registrar URL en `apps/reporting/urls.py`.

- [ ] 4.2 Action `anotar_retorno` en
  `apps/academic_tracking/views.py`:
  `PATCH /api/academic-tracking/records/{id}/anotar_retorno/`
  con body `{"retorno_archipelago": true|false}`.
  Permiso: `_AcademicManagementPermission` (R-COORD/R-ADMIN).
  Usar `transaction.atomic`; rollback si `log_audit_event` falla
  (fail-closed). Audit action `academic_retorno_annotate`.

- [ ] 4.3 Tests de endpoints:

  `apps/reporting/tests/test_estudio_impacto.py`:
  - `test_r_ct_200`, `test_anonimo_401`, `test_sin_rol_403`.
  - `test_params_invalidos_400_anio_inicio_faltante`,
    `test_params_invalidos_400_rango_invalido`.

  `apps/academic_tracking/tests/test_retorno_anotacion.py`:
  - `test_anotacion_retorno_genera_audit`.
  - `test_anotacion_audit_fail_rollback` (patch
    `log_audit_event` para que falle).
  - `test_permiso_escritura_sin_rol_403`.

## 5. Verificación final

- [ ] 5.1 Suite completa verde en SQLite (`pytest --ds=config.settings_sqlite`);
  CI ejecuta en PostgreSQL (`pytest --ds=config.settings`).

- [ ] 5.2 `manage.py check` sin errores;
  `makemigrations --check` confirma que no hay migraciones
  pendientes tras aplicar las del change.

- [ ] 5.3 Documentar limitación de variantes de nombre de IES
  (sinónimos) en el docstring del servicio como nota técnica.
