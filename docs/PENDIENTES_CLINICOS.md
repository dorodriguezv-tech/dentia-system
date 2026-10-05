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
