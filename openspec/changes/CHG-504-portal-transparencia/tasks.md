# Tasks — CHG-504: Portal de Transparencia (CAP-021)

## 1. Selectores públicos (apps/reporting/)

- [ ] 1.1 Crear `apps/reporting/selectors/transparencia.py` con
  `TransparenciaSelectors.actos_publicados()` — filtra
  `ActoAdministrativo.estado=PUBLICADO`, no serializa nombres ni
  documentos, incluye `pdf_url`
- [ ] 1.2 `TransparenciaSelectors.convocatorias_abiertas_cerradas()` —
  queryset de `Convocatory` con estados `ABIERTA` y `CERRADA`,
  incluye `nombre`, `codigo`, `estado`, `fecha_apertura`,
  `fecha_cierre`
- [ ] 1.3 `TransparenciaSelectors.estadisticas_agregadas(anio=None)`
  — reutiliza métodos de `ReportingService` para totales por año/estado;
  primera iteración sin desglose IES/municipio
- [ ] 1.4 `TransparenciaSelectors.estadisticas_portal()` — compose de
  KPIs públicos para landing page

## 2. Portal HTML (templates/transparencia/)

- [ ] 2.1 `templates/transparencia/base.html` — extiende
  `templates/base.html`, incluye navbar con enlaces a actos,
  convocatorias y estadísticas
- [ ] 2.2 `templates/transparencia/index.html` — landing
  `/transparencia/` con cifras resumen (convocatorias activas,
  beneficiarios agregados, actos publicados) y accesos directos
- [ ] 2.3 `templates/transparencia/actos.html` — listado paginado de
  actos publicados con número, fecha y enlace al PDF; paginate_by
  configurado
- [ ] 2.4 `templates/transparencia/convocatorias.html` — listado
  paginado de convocatorias abiertas/cerradas con estado y fechas
- [ ] 2.5 `templates/transparencia/estadisticas.html` — gráficas y
  tablas de totales agregados por año/estado (sin IES/municipio);
  selector de año
- [ ] 2.6 Actualizar `templates/base.html` para incluir enlace
  "Transparencia" en la navegación

## 3. API pública JSON

- [ ] 3.1 Crear serializadores en `apps/reporting/serializers.py`:
  `TransparenciaActoSerializer` (sin campos PII), `TransparenciaConvocatoriaSerializer`,
  `TransparenciaEstadisticaSerializer`
- [ ] 3.2 Vistas DRF en `apps/reporting/views.py`:
  `TransparenciaActosView`, `TransparenciaConvocatoriasView`,
  `TransparenciaEstadisticasView` con `permission_classes = [AllowAny]`
- [ ] 3.3 Registrar URLs en `apps/reporting/urls.py` bajo la ruta
  `api/transparencia/`
- [ ] 3.4 Asegurar que los serializadores nunca serializan campos
  `nombre`, `documento`, `email`, `datos_beneficiario`,
  `datos_academicos`

## 4. URLs y navegación

- [ ] 4.1 Registrar rutas en `apps/reporting/urls.py`:
  `/transparencia/`, `/transparencia/actos/`,
  `/transparencia/convocatorias/`, `/transparencia/estadisticas/`
- [ ] 4.2 Incluir URLs en el root `urls.py` bajo `transparencia/`
- [ ] 4.3 Añadir enlace "Transparencia" en `templates/base.html`

## 5. Pruebas

- [ ] 5.1 Unitarias de selectores: cada método de
  `TransparenciaSelectors` devuelve únicamente campos documentados;
  aserción PII-negativa (nombres, emails, documentos nunca en
  resultado) con datos sintéticos
- [ ] 5.2 Integración HTML anónima: `APIClient` sin autenticar accede a
  las 4 páginas del portal → todas devuelven HTTP 200
- [ ] 5.3 Integración API anónima: `APIClient` sin autenticar accede a
  los 3 endpoints JSON → todos devuelven HTTP 200
- [ ] 5.4 Test solo actos PUBLICADO: crear acto en estado BORRADOR,
  verificar que no aparece en `/api/transparencia/actos/` ni en
  `/transparencia/actos/`
- [ ] 5.5 Tests de aserción PII-negativa (patrón
  `test_reports.py:test_respuesta_sin_pii`): búsqueda de strings de
  datos sintéticos (nombres, documentos, emails) en respuestas HTML y
  JSON
- [ ] 5.6 Suite completa verde en sqlite y PostgreSQL

## 6. Verificación final

- [ ] 6.1 `pytest apps/reporting/tests/test_transparencia*.py` — todos
  verdes
- [ ] 6.2 `python manage.py check` — sin errores
- [ ] 6.3 `python manage.py makemigrations --check` — sin cambios
  pendientes (no hay modelos nuevos)
- [ ] 6.4 Revisión manual: navegar incognito todas las páginas del
  portal y verificar ausencia visual de nombres/documentos
