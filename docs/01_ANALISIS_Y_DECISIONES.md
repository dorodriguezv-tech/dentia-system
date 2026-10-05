# Análisis de los documentos de contexto y decisiones

## 1. Documentos analizados
| Documento | Propósito | Aporte principal |
|---|---|---|
| Especificaciones Base v1.0 (29-sep-2026) | Anteproyecto clínico-técnico | Alcance completo, NOM aplicables, roles, modelo conceptual, API base, reglas de integridad, MVP |
| Especificación v2.0 | Especificación ejecutable | Rutas A/B/C respecto a Open Dental, orden de implementación, backlog MVP-01…12, odontograma por eventos, notas por estados |
| Presentación para odontólogos | Validación clínica | Experiencia del odontólogo, flujo de consulta en 12 pasos, preguntas que debe responder la clínica |

## 2. Hallazgos del análisis
1. **Los tres documentos son coherentes en el alcance.** El núcleo es expediente + odontograma + flujo de atención, y el MVP es prácticamente idéntico en v1 y v2.
2. **Hay una contradicción tecnológica.** La v2 recomienda .NET/C# + MariaDB para acercarse a Open Dental, mientras que la v1 y la petición actual piden Python + PostgreSQL + web. Se resuelve con la **Ruta B: implementación independiente**:
   - No se copia ni deriva código de Open Dental, así que no hay obligaciones GPL ni riesgo con la versión 24.4+, que es propietaria.
   - Open Dental y Dentrix se usan **solo** como referencia funcional y de experiencia de uso.
   - La v2 misma acepta esta ruta (“PostgreSQL + FastAPI continúa siendo una alternativa válida”).
3. **El asistente de IA se adelanta respecto al roadmap.** Los documentos dejan la IA en la Fase 3/4, pero la petición la hace prioritaria. Es compatible con lo que los documentos permiten desde el inicio: asistencia **documental** (dictado → borrador estructurado) con validación humana. **No** se incluye sugerencia diagnóstica autónoma.
4. **El procesamiento local con Ollama favorece el cumplimiento.** No hay transferencia de datos de salud (datos sensibles según la LFPDPPP 2025) a terceros. Esto reduce riesgos legales, aunque no sustituye la revisión jurídica.
5. **Hay marcadores de cita rotos** en la presentación y la v2 (`fileciteturn…`, `citeturn…`). Conviene limpiarlos antes de entregar esos documentos a la clínica.
6. **Faltan definiciones clínicas** (sección 13 de la presentación y 28 de la v1). El sistema debe arrancar con **catálogos configurables** para no bloquear el desarrollo.

## 3. Decisiones (ADR-001)
| Tema | Decisión |
|---|---|
| Ruta legal | B — Implementación independiente |
| Stack | FastAPI + PostgreSQL + React/TS (Vite) |
| Arquitectura | Monolito modular con vertical slices (evitar microservicios prematuros) |
| Notación dental | FDI |
| IA | Local: faster-whisper (voz→texto) + Ollama (texto→acciones JSON). Siempre como propuesta con confirmación humana |
| Personalización | Nombre, logo y paleta configurables por clínica desde la interfaz |
| Despliegue inicial | Servidor local de la clínica (on-premise), porque el agente de IA usa el equipo local; la nube queda para después |

## 4. Alcance del MVP (orden de construcción)
1. Base del proyecto, IAM, sucursales y auditoría
2. Tema y marca (colores y logo)
3. Pacientes y duplicados
4. Expediente: antecedentes, alergias, medicamentos, alertas, atenciones y notas
5. Odontograma (permanente y temporal, por superficie, con historial)
6. Agenda (citas, estados, conflictos)
7. Diagnóstico y plan de tratamiento con presupuesto
8. **Agente de IA por voz**
9. Consentimientos, documentos e imágenes básicas
10. Cobranza básica
11. Reportes básicos, respaldos y restauración
12. Pruebas E2E del flujo completo y endurecimiento

Fase 2 (fuera del MVP): periodontograma, CFDI, inventario, laboratorio, portal del paciente, mensajería y DICOM/PACS.

## 5. Normativa a considerar (requiere validación jurídica)
- NOM-004-SSA3-2012 (expediente clínico)
- NOM-013-SSA2-2015 (enfermedades bucales)
- NOM-024-SSA3-2012 (sistemas de registro electrónico para la salud)
- LFPDPPP publicada el 20-mar-2025 (datos sensibles, aviso de privacidad, derechos ARCO)

Este documento no es dictamen legal.

## 6. Decisiones pendientes con el odontólogo
Se registran en `docs/PENDIENTES_CLINICOS.md` conforme aparezcan:
- Información visible al abrir un paciente
- Campos obligatorios en la primera consulta
- Estados y símbolos del odontograma
- Especialidades y catálogo de procedimientos y precios
- Plantillas de notas y consentimientos
- Tipos de fotografía y radiografía usados
- Vocabulario y frases habituales de dictado (para afinar el asistente de voz)
