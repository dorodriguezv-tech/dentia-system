# Pendientes clínicos por validar con el odontólogo

| # | Pregunta | Valor provisional en el sistema | Fase que afecta | Respuesta |
|---|---|---|---|---|
| 1 | ¿Qué información debe verse al abrir un paciente? | Nombre, edad, alertas, última atención, tratamientos pendientes, saldo | 3–4 | |
| 2 | ¿Qué campos son obligatorios en la primera consulta? | Identificación, motivo, alergias, medicamentos, antecedentes relevantes | 4 | |
| 3 | ¿Qué estados y símbolos maneja el odontograma? | 12 estados base configurables (ver Fase 5) | 5 | |
| 4 | ¿Cómo documenta hoy una consulta? | Nota SOAP + texto libre | 4 | |
| 5 | ¿Qué especialidades y procedimientos hay desde el inicio? | Catálogo general editable | 7 | |
| 6 | ¿Qué tipos de fotografía y radiografía usa? | Intraoral, extraoral, periapical, bitewing, panorámica, cefalometría | 9 | |
| 7 | ¿Qué consentimientos se necesitan? | General, extracción, endodoncia, anestesia (plantillas editables) | 9 | |
| 8 | ¿Qué reportes necesita para decidir? | Ver Fase 11 | 11 | |
| 9 | ¿Qué frases usa al dictar? (10–20 ejemplos reales, sin datos de pacientes) | Corpus ficticio | 8 | |
| 10 | ¿Dentición mixta: cómo prefiere visualizarla? | Vista mixta con temporales sobre permanentes | 5 | |
| 11 | ¿Qué permiso exacto debe tener cada rol (recepción, caja, asistente, etc.)? | Matriz por defecto en `docs/MATRIZ_PERMISOS.md`, generada de `backend/app/modules/iam/permissions_catalog.py` | 1 | |
| 12 | Si la organización tiene varias sucursales con marca distinta, ¿qué nombre/logo se muestra en `GET /branding` (pantalla de login, antes de elegir sucursal)? | Se usa la sucursal creada primero (`clinics.created_at` más antiguo); solo importa si hay mas de una sucursal con branding propio | 2 | |
| 13 | ¿Qué tan parecido debe ser un nombre para avisar de un posible paciente duplicado? ¿Y qué datos son obligatorios al dar de alta (más allá de nombre y fecha de nacimiento)? | Similitud de nombre (`pg_trgm`) > 0.4, combinada con misma fecha de nacimiento o mismo teléfono; obligatorios solo nombre(s), apellido paterno y fecha de nacimiento | 3 | |
| 14 | ¿Qué palabras clave en medicamentos/antecedentes deben disparar una alerta crítica al finalizar una nota, y con qué texto exacto debe mostrarse cada una? | Catálogo inicial en `backend/app/modules/records/rules.py` (`CONDITION_ALERT_KEYWORDS`, `MEDICATION_ALERT_KEYWORDS`): diabetes, embarazo, hipertensión, marcapasos, hemofilia, VIH, hepatitis, epilepsia y cardiopatía como antecedentes; anticoagulantes (warfarina, acenocumarina, rivaroxabán, apixabán), antiagregantes (clopidogrel, aspirina), insulina, bifosfonatos, corticoesteroides e inmunosupresores como medicamentos. Toda alergia activa alerta siempre, sin importar la sustancia | 4 | |
| 15 | Al registrar un hallazgo de "toda la pieza" (p.ej. ausente, implante), ¿deben anularse automáticamente los hallazgos vigentes por superficie que ya tuviera esa misma pieza? | No por ahora: coexisten en la base (cada uno con su propia clave pieza+superficie+tipo); el frontend solo prioriza visualmente el hallazgo de toda la pieza sobre los de superficie al dibujar el odontograma, pero ambos siguen "vigentes" y aparecen en el historial | 5 | |
| 16 | ¿El canino (posición 3 de cada cuadrante) debe tratarse como pieza anterior (superficie incisal) o posterior (superficie oclusal) en el odontograma? | Se trata como anterior (incisal), junto con los incisivos (posiciones 1 y 2) — ver `backend/app/modules/odontogram/rules.py` (`_ANTERIOR_POSITIONS`) | 5 | |
| 17 | ¿Debe impedirse agendar una cita fuera del horario laboral del profesional o sobre un bloqueo (vacaciones, permiso), o solo advertir? | Solo advierte (`warnings` no bloqueantes en la respuesta de crear/reprogramar una cita); no impide guardar. El horario laboral y los bloqueos son por profesional, no por gabinete | 6 | |
| 18 | ¿Qué tipos de cita y duración por defecto deben existir, y cómo se relacionan con el catálogo de procedimientos de la Fase 7? | Catálogo provisional en `backend/app/modules/agenda/rules.py` (`APPOINTMENT_TYPES`): consulta/valoración (30 min), limpieza (45), restauración (60), endodoncia (90), extracción (45), control de ortodoncia (20), prótesis (60), urgencia (30). Debe unificarse con el catálogo real de procedimientos y precios cuando se construya la Fase 7 | 6 | |
