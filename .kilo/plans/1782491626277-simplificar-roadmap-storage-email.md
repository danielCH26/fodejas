# Plan: Simplificar Roadmap - Eliminar S3 Prod y Email Transaccional

## Resumen
Eliminar INF-008 (S3 storage prod) e INF-009 (email transaccional) del roadmap de Fase 0. Los anexos se almacenan localmente con MinIO en dev y volúmenes locales en prod. Las notificaciones son solo in-app (web).

## Decisiones Concretas
1. **Almacenamiento**: MinIO local para dev, volúmenes Docker en prod (sin S3 externo)
2. **Notificaciones**: Solo in-app web, sin email, sin push

---

## Cambios en roadmap.md

### 1. Sección 4.1 - Tabla de Cambios INF

**Eliminar filas:**
- INF-008: `INF-008-storage-prod` — Storage S3-compatible de producción
- INF-009: `INF-009-email-transactional` — Email transaccional

**Agregar fila (simplificado):**
- INF-008: `INF-008-storage-local` — Almacenamiento local con MinIO en dev, volúmenes Docker en prod

### 2. Sección 4.1 - Descripción de INF-008 Actual
```
| INF-008   | `INF-008-storage-prod`         | Storage S3-compatible de producción: bucket de anexos, versionado, cifrado en reposo, ciclo de vida |
```

**Cambiar a:**
```
| INF-008   | `INF-008-storage-local`        | Almacenamiento local: MinIO en dev, volúmenes Docker en prod, sin costos S3 |
```

### 3. Sección 4.1 - Descripción de INF-009
**Eliminar completamente** la fila INF-009.

### 4. Sección 4.2 - Entregables Verificables

**Eliminar:**
- "[ ] El bucket de anexos tiene versionado, cifrado y política de ciclo de vida."
- "[ ] El dominio de email está verificado (DKIM/SPF/DMARC) y los correos transaccionales salen firmados."

**Agregar:**
- "[ ] Los anexos se almacenan localmente usando MinIO en dev y volúmenes Docker en prod."

### 5. Sección 4.2 - Entregables de Email (INF-009)
**Eliminar:**
- "[ ] El dominio de email está verificado (DKIM/SPF/DMARC) y los correos transaccionales salen firmados."

### 6. Agregar nota sobre notificaciones

En sección 4 (después de 4.2) o en sección 1 (Principios), agregar:
> **Nota sobre notificaciones**: Todas las notificaciones son in-app (pestaña de notificaciones en la plataforma web). No se implementa email transaccional ni notificaciones push.

---

## Cambios en project.md

### 1. Sección 4 - Stack Tecnológico

**Línea actual:**
```
| **Almacenamiento**    | **S3-compatible** (MinIO en dev) para anexos digitales      |
```

**Cambiar a:**
```
| **Almacenamiento**    | **MinIO local** (dev) y volúmenes Docker (prod) para anexos digitales |
```

### 2. Sección 4.1 - Principios Arquitectónicos
**Agregar al final:**
- **Notificaciones in-app**: todas las notificaciones al usuario se muestran en la pestaña de notificaciones dentro de la plataforma. No se envían correos electrónicos.

### 3. Sección 8.1 - Nota sobre Integraciones Externas

**Agregar al final:**
- **Email**: no se implementa envío de emails transaccionales. Todas las notificaciones son in-app.

---

## Tareas de Implementación

### En roadmap.md:
- [ ] 1. Eliminar fila INF-008-storage-prod de la tabla 4.1
- [ ] 2. Agregar fila INF-008-storage-local simplificada
- [ ] 3. Eliminar fila INF-009-email-transactional de la tabla 4.1
- [ ] 4. Actualizar entregables verificables (sección 4.2)
- [ ] 5. Agregar nota sobre notificaciones in-app

### En project.md:
- [ ] 6. Actualizar stack tecnológico - columna almacenamiento
- [ ] 7. Agregar principio de notificaciones in-app
- [ ] 8. Agregar nota sobre no-integración de email

---

## Archivos Afectados

### Documents principales (cambios vivos)
- `roadmap.md` — líneas ~163-176 (tabla INF), ~186-224 (entregables)
- `project.md` — líneas ~305-316 (stack), ~616-627 (integraciones)

### Changes archivados a revisar
Buscar en `openspec/changes/archive/` cualquier mention de S3 o email:

| Change | Campo a verificar |
|--------|------------------|
| `inf-004-environments` | specs/postgres-tuning/spec.md si menciona S3 |
| `inf-006-observability` | proposal.md, specs/postgres-monitoring/spec.md — verificar que no requiera S3 |
| `inf-007-postgres-prod` (ya archivado) | specs/postgres-backup/spec.md — puede mantener MinIO local |

**Acción**: Si algún spec.md de archive menciona S3 como requisito de producción, actualizar a "almacenamiento local".

---

## Validación
1. Buscar `INF-008` y `INF-009` en todo el repo — deben estar solo en archivos de archive
2. Buscar `S3` o `s3` en specs — no debe aparecer como requisito de producción
3. Buscar `email` o `email transaccional` — no debe aparecer como requisito
4. Verificar que `MinIO` aparece solo para desarrollo local
5. Verificar que `pgbouncer` está en archives relevantes (INF-007)
