# Estado de Aceptación del MVP — Piloto FODEJAS

> Documento de aceptación generado en la sesión del 2026-10-09/10.
> MVP definido como: ejecutar la convocatoria piloto «Reconocimiento a la
> Excelencia» end-to-end sin papel hasta la orden de pago
> (publicación → postulación FUI → validación → scoring →
> reclamaciones/apelaciones → resultados definitivos → acto firmado →
> legalización del crédito → orden de pago a Tesorería).

## 1. Alcance implementado

| Capacidad | Cambio | Estado |
| --- | --- | --- |
| CAP-029 Firma electrónica | CHG-301 | ✅ completo (41 tests) |
| CAP-009 Legalización | CHG-302 | ✅ completo (80 tests) |
| CAP-010 Desembolsos | CHG-303 | ✅ completo (64 tests) |
| CAP-002..008 Piloto (Fase 2) | CHG-201..208 | ✅ cerrados (e2e de governance en suite) |
| CAP-022 Auditoría | CHG-801 | ✅ cadena con hash + actor |
| CAP-001 Auth/RBAC | CHG-101/112/113 | ✅ |

## 2. Estado de verificación

- Suite completa: **419 passed / 8 skipped / 0 failed / 0 errors**
  (~22-43s; hasher MD5 en tests).
- `python manage.py check`: limpio.
- `python manage.py makemigrations --check`: limpio.
- `ruff check .`: 35 ítems aceptados como deuda documentada
  (27 E402 imports tras setup dinámico en scripts, 6 C901 estructura
  compleja, 2 B017 asserts ciegos en tests). `black`/`isort` no
  instalados en el host de desarrollo.
- Comandos de verificación del CHG-208 §8: ejecutados y en verde
  (ast checks, suite, `manage.py check`).

## 3. Flujos e2e cubiertos por tests

1. **Piloto Fase 2** (`apps/governance/tests/test_pilot_e2e.py`):
   flujo completo del acto administrativo con workflow de firmas y
   modificatorio posterior a la publicación.
2. **Firma electrónica**
   (`apps/legalization/tests/test_api.py::test_e2e_create_sign_verify_audit_flow`):
   creación → firma → verificación de cadena de hashes → evento de
   auditoría.
3. **Legalización**
   (`apps/legalization/tests/test_services.py`): creación de los 3
   documentos por beneficiario → generación de PDF → completado →
   cancelación; detección de tamper post-firma.
4. **Desembolsos** (`apps/treasury/tests/`): doble firma (sin
   autofirma, en ambas direcciones) → orden con 4 adjuntos →
   conciliación manual con comprobante → sweep VENCIDO a 5 días
   hábiles.

## 4. Simplificaciones conocidas y riesgos

| # | Simplificación | Impacto | Seguimiento |
| --- | --- | --- | --- |
| 1 | 4° adjunto asumido como `ACTO_ADMINISTRATIVO` | Bajo — supuesto documentado en `tasks.md` de CHG-303 | Confirmar contra el workflow de actos de governance |
| 2 | Llamadas de auditoría de treasury envueltas en `try/except` | Medio — una falla de auditoría no revierte la transacción | Revisar en la revisión del stack; evaluar atomicidad compartida |
| 3 | `tesoreria_alert_v5d` sin canal de notificación | Medio — el sweep marca VENCIDO pero no alerta | Conectar a CAP-019 (notificaciones, diferido) |
| 4 | Render real de WeasyPrint no verificado en host dev | Medio — los 80 tests usan seam; falta validar PDF real | Ejecutar en CI/contenedor con librerías GTK |
| 5 | Firma síncrona (sin Celery) | Bajo — decisión de diseño del MVP | Revisar si el volumen del piloto lo exige |

## 5. Pendientes de despliegue

- PostgreSQL en producción (el desarrollo/tests corren sobre SQLite).
- WeasyPrint requiere librerías GTK en la imagen Docker de producción.
- Worker + beat de Celery activos para los sweeps de plazos
  (CHG-802) en staging/producción.
- Ejecutar `python manage.py check_signer_config` en staging:
  debe abortar si `SIGNATURE_PROVIDER=mock`.
- Cabeceras de seguridad y gunicorn ya configurados (CHG-803);
  validar en el deploy de staging.

## 6. Próximos pasos

1. Revisión del stack local (4 ramas apiladas, ~46 commits) en
   **PRs encadenados por commit** (skill `chained-pr`): los cortes
   naturales están documentados en `odd/tasks/mvp-route.md`.
2. Push a origin: **decisión del usuario** (origin/master está 13+
   commits atrás).
3. Post-MVP (backlog): CHG-304 (causales de terminación), CHG-401
   (seguimiento académico), Fases 4–5, apps de reporting/
   transparencia, runbooks/DRP (INF-011/012/015).
