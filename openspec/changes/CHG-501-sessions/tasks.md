# Tasks — CHG-501: Sesiones de Junta y Comité Técnico

## 1. Modelos

- [x] 1.1 Crear `Sesion` (tipo, órgano JUNTA/CT, fecha, estado
      CONVOCADA/EN_SESION/FINALIZADA/ANULADA, convocatoria_enviada_at)
- [x] 1.2 Crear `MiembroSesion` (asistencia, exención por cargo,
      conflicto declarado flag)
- [x] 1.3 Crear `OrdenDelDiaPunto` (numeración, texto, resultado)
- [x] 1.4 Crear `Voto` (A_FAVOR/EN_CONTRA/ABSTENCION por punto)
- [x] 1.5 Crear `ActaSesion` (PDF, hash SHA-256, firmantes, estado firma)
- [x] 1.6 Migraciones

## 2. Servicios

- [x] 2.1 `convocar_sesion` con anticipos 5/2 días hábiles (Art. §6.1.1)
- [x] 2.2 `registrar_asistencia` + quorum (mitad + 1 con
      derecho a voto; exentos por cargo no votan)
- [x] 2.3 `abrir_sesion` (guard de quórum) / `finalizar_sesion` /
      `anular_sesion`
- [x] 2.4 `agregar_punto` / `registrar_voto` (excluye exentos y
      conflictos) / `cerrar_punto` (mayoría simple)
- [x] 2.5 `generar_acta` (PDF + SHA-256, patrón governance pdf) /
      `firmar_acta` (CAP-029)
- [x] 2.6 Auditoría CAP-022 en cada transición (fail-closed)

## 3. API

- [ ] 3.1 ViewSets + serializers (Sesion con puntos/votos anidados,
      ActaSesion)
- [ ] 3.2 Matriz de roles: gestión R-JUNTA/R-ADMIN; asistencia y voto
      solo miembro propio; actas R-JUNTA/R-ADMIN/R-CT/R-OFIJUR

## 4. Testing

- [x] 4.1 Unitarias: quórum, anticipos, mayoría simple, exenciones,
      exclusión por conflicto, hash del acta
- [ ] 4.2 Integración: flujo completo + gating de API
- [x] 4.3 Suite completa verde en sqlite (476 tests pass, 8 skipped)

## 5. Cierre

- [x] 5.1 tasks.md conciliado con evidencia
- [ ] 5.2 roadmap.md §9.2 entregable marcado
- [ ] 5.3 PR + CI verde + merge
