"""Marcador (placeholder) para CAP-017 — Sesiones de Junta y CT.

Este paquete se crea en CHG-806 para evitar `ModuleNotFoundError`
inesperado cuando un dev futuro intente importar algo de aquí. La
implementación real (modelos Sesion/OrdenDelDia/Voto/Quorum/ActaSesion,
servicios de quórum y votación, vistas de sesiones) queda **diferida
a Fase 5** y se implementará en `CHG-501-sessions` según
`roadmap.md §9.1`.

Cualquier archivo adicional dentro de este paquete debe justificarse
en una propuesta OpenSpec aprobada. No agregar modelos, signals ni
servicios hasta entonces.
"""
