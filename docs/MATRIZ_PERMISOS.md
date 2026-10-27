# Matriz de permisos (CLAUDE.md sec. 5)

Generada a partir de `backend/app/modules/iam/permissions_catalog.py`
(unica fuente de verdad: para cambiar la matriz, edita ese archivo y
vuelve a generar este documento). Es un catalogo configurable: los valores
por defecto deben validarse con la clinica antes de produccion
(ver docs/PENDIENTES_CLINICOS.md).

| Permiso | Descripcion | Super administrador | Administrador de la clinica | Odontologo | Especialista | Asistente dental | Recepcion | Caja |
|---|---|---|---|---|---|---|---|---|
| `iam.manage_organizations` | Crear y administrar organizaciones | X |  |  |  |  |  |  |
| `iam.manage_clinics` | Crear y administrar sucursales | X |  |  |  |  |  |  |
| `iam.manage_users` | Crear, editar y asignar roles a usuarios de la clinica | X | X |  |  |  |  |  |
| `iam.view_users` | Ver usuarios de la clinica | X | X |  |  |  |  |  |
| `audit.read` | Consultar la bitacora de auditoria | X | X |  |  |  |  |  |
| `branding.manage` | Editar nombre, logo y colores de la clinica | X | X |  |  |  |  |  |
| `document_settings.manage` | Editar los logos, titulo institucional y lugar del encabezado de los documentos impresos | X | X |  |  |  |  |  |
| `patients.read` | Ver pacientes |  | X | X | X | X | X | X |
| `patients.write` | Crear y editar pacientes |  | X | X |  |  | X |  |
| `records.read` | Ver el expediente clinico |  |  | X | X |  |  |  |
| `records.write` | Editar el expediente clinico |  |  | X | X |  |  |  |
| `odontogram.read` | Ver el odontograma |  |  | X | X | X |  |  |
| `odontogram.write` | Editar el odontograma |  |  | X | X |  |  |  |
| `agenda.read` | Ver la agenda |  | X | X | X | X | X |  |
| `agenda.write` | Crear y modificar citas |  | X | X | X |  | X |  |
| `diagnosis.read` | Ver diagnosticos |  |  | X | X |  |  |  |
| `diagnosis.write` | Registrar diagnosticos |  |  | X | X |  |  |  |
| `treatment.read` | Ver planes de tratamiento y presupuestos |  | X | X | X |  |  |  |
| `treatment.write` | Crear planes de tratamiento |  |  | X | X |  |  |  |
| `treatment.accept_budget` | Aceptar o rechazar presupuestos |  |  | X | X |  |  |  |
| `documents.read` | Ver documentos y consentimientos |  | X | X | X |  |  |  |
| `documents.write` | Generar documentos y consentimientos |  |  | X | X |  |  |  |
| `documents.sign` | Firmar consentimientos |  |  | X | X |  |  |  |
| `imaging.read` | Ver imagenes y radiografias |  |  | X | X | X |  |  |
| `imaging.write` | Cargar imagenes y radiografias |  |  | X | X | X |  |  |
| `billing.read` | Ver cargos, pagos y saldos |  | X |  |  |  | X | X |
| `billing.write` | Registrar cargos y pagos |  | X |  |  |  |  | X |
| `billing.configure` | Activar o desactivar la cobranza de la sucursal |  | X |  |  |  |  |  |
| `reports.read` | Ver reportes | X | X |  |  |  |  | X |
| `catalogs.manage` | Administrar catalogos de la clinica (tipos de cita, hallazgos, diagnosticos...) |  | X |  |  |  |  |  |
| `ai.use` | Usar el asistente de IA por voz |  |  | X | X |  |  |  |
| `ai.configure` | Configurar el asistente de IA |  | X |  |  |  |  |  |
| `voice.use` | Usar el asistente de voz Dentia (navegacion, agenda y pacientes) |  |  | X | X |  | X |  |
| `voice.clinical` | Usar Dentia para capturar datos clinicos (odontograma, diagnosticos...) |  |  | X | X |  |  |  |
