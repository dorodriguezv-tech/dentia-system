# ADR-001 — Ruta B (implementación independiente) y stack Python/PostgreSQL/React

## Estado
Aceptado.

## Contexto
Existen tres documentos de contexto para este proyecto (especificación base v1.0, especificación
v2.0 y una presentación de validación con odontólogos). Los tres coinciden en el alcance — el
núcleo es expediente clínico + odontograma + flujo de atención — pero la v2.0 recomienda un
stack .NET/C# + MariaDB para acercarse a Open Dental, mientras que la petición del proyecto y la
v1.0 piden Python + PostgreSQL + web. Ver el detalle completo en
[`docs/01_ANALISIS_Y_DECISIONES.md`](../01_ANALISIS_Y_DECISIONES.md).

## Decisión
1. **Ruta B — implementación independiente.** No se copia ni deriva código de Open Dental ni de
   ningún otro sistema existente. Open Dental y Dentrix se usan únicamente como referencia
   funcional y de experiencia de uso. Esto evita obligaciones de licenciamiento (GPL) y riesgos
   con versiones propietarias.
2. **Stack:** Python 3.12 + FastAPI + SQLAlchemy 2 (async) + PostgreSQL 16 en el backend;
   React 18 + TypeScript + Vite en el frontend. La propia especificación v2.0 acepta esta
   alternativa ("PostgreSQL + FastAPI continúa siendo una alternativa válida").
3. **Arquitectura:** monolito modular organizado por *vertical slices* (un paquete por módulo de
   negocio), evitando microservicios prematuros mientras el equipo y el volumen de datos sean
   pequeños.
4. **Notación dental:** FDI (11–48 permanentes, 51–85 temporales) en todo el sistema.
5. **IA local:** faster-whisper (voz → texto) y Ollama (texto → acciones JSON) corriendo en el
   equipo de la clínica, sin llamadas a servicios externos. La IA siempre propone; una acción
   humana confirma antes de guardar (reglas 9 y 10 de `CLAUDE.md`).
6. **Despliegue inicial:** servidor local de la clínica (on-premise), porque el asistente de IA
   depende del equipo local. La nube queda para una fase posterior.

Cualquier cambio a este stack requiere un nuevo ADR en `docs/adr/`.

## Consecuencias
- Se renuncia a la compatibilidad binaria o de base de datos con Open Dental; cualquier
  migración de datos desde otro sistema se resuelve con scripts de importación propios.
- El equipo necesita experiencia en Python async y en React/TypeScript, no en .NET.
- El procesamiento local de IA impone requisitos de hardware en el servidor de la clínica
  (16 GB de RAM recomendados; GPU NVIDIA opcional) en vez de depender de un proveedor externo.
- La revisión jurídica (NOM-004, NOM-024, LFPDPPP 2025) sigue pendiente y es independiente de
  esta decisión técnica.
