"""Catalogo de roles y permisos (CLAUDE.md sec. 5) y la matriz rol->permiso.

Es la unica fuente de verdad: la migracion de datos y docs/MATRIZ_PERMISOS.md
se generan a partir de aqui. Es un catalogo configurable (CLAUDE.md sec. 7):
la asignacion default de permisos por rol debe validarse con la clinica
(ver docs/PENDIENTES_CLINICOS.md).
"""

ROLES: dict[str, str] = {
    "superadmin": "Super administrador",
    "admin_clinica": "Administrador de la clinica",
    "odontologo": "Odontologo",
    "especialista": "Especialista",
    "asistente": "Asistente dental",
    "recepcion": "Recepcion",
    "caja": "Caja",
    # A peticion del operador: cuenta de demostracion de tiempo limitado
    # (User.expires_at) que ve y puede entrar a cualquier pantalla del
    # sistema -- unico rol con TODOS los permisos. Vive en su propia
    # sucursal dedicada que se reinicia a un estado de ejemplo en cada login
    # (ver iam/service.py::reset_demo_clinic); ademas, las acciones que
    # podrian afectar el funcionamiento (borrar/editar otros usuarios) quedan
    # visibles pero no se ejecutan de verdad para este rol (misma funcion).
    "demo": "Demostracion (temporal)",
}

PERMISSIONS: dict[str, str] = {
    "iam.manage_organizations": "Crear y administrar organizaciones",
    "iam.manage_clinics": "Crear y administrar sucursales",
    "iam.manage_users": "Crear, editar y asignar roles a usuarios de la clinica",
    "iam.view_users": "Ver usuarios de la clinica",
    "audit.read": "Consultar la bitacora de auditoria",
    "branding.manage": "Editar nombre, logo y colores de la clinica",
    "document_settings.manage": (
        "Editar los logos, titulo institucional y lugar del encabezado de los"
        " documentos impresos"
    ),
    "version_info.read": "Ver la version de DentalCare desplegada",
    "patients.read": "Ver pacientes",
    "patients.write": "Crear y editar pacientes",
    "records.read": "Ver el expediente clinico",
    "records.write": "Editar el expediente clinico",
    "odontogram.read": "Ver el odontograma",
    "odontogram.write": "Editar el odontograma",
    "agenda.read": "Ver la agenda",
    "agenda.write": "Crear y modificar citas",
    "diagnosis.read": "Ver diagnosticos",
    "diagnosis.write": "Registrar diagnosticos",
    "treatment.read": "Ver planes de tratamiento y presupuestos",
    "treatment.write": "Crear planes de tratamiento",
    "treatment.accept_budget": "Aceptar o rechazar presupuestos",
    "documents.read": "Ver documentos y consentimientos",
    "documents.write": "Generar documentos y consentimientos",
    "documents.sign": "Firmar consentimientos",
    "imaging.read": "Ver imagenes y radiografias",
    "imaging.write": "Cargar imagenes y radiografias",
    "billing.read": "Ver cargos, pagos y saldos",
    "billing.write": "Registrar cargos y pagos",
    "billing.configure": "Activar o desactivar la cobranza de la sucursal",
    "reports.read": "Ver reportes",
    "ai.use": "Usar el asistente de IA por voz",
    "ai.configure": "Configurar el asistente de IA",
    "catalogs.manage": (
        "Administrar catalogos de la clinica (tipos de cita, hallazgos, diagnosticos...)"
    ),
    "voice.use": "Usar el asistente de voz Dentia (navegacion, agenda y pacientes)",
    "voice.clinical": "Usar Dentia para capturar datos clinicos (odontograma, diagnosticos...)",
}

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "superadmin": (
        "iam.manage_organizations",
        "iam.manage_clinics",
        "iam.manage_users",
        "iam.view_users",
        "audit.read",
        "branding.manage",
        "document_settings.manage",
        "version_info.read",
        "reports.read",
    ),
    "admin_clinica": (
        "iam.manage_users",
        "iam.view_users",
        "audit.read",
        "branding.manage",
        "document_settings.manage",
        "version_info.read",
        "patients.read",
        "patients.write",
        "agenda.read",
        "agenda.write",
        "billing.read",
        "billing.write",
        "billing.configure",
        "documents.read",
        "treatment.read",
        "reports.read",
        "ai.configure",
        "catalogs.manage",
    ),
    "odontologo": (
        "patients.read",
        "patients.write",
        "records.read",
        "records.write",
        "odontogram.read",
        "odontogram.write",
        "diagnosis.read",
        "diagnosis.write",
        "treatment.read",
        "treatment.write",
        "treatment.accept_budget",
        "documents.read",
        "documents.write",
        "documents.sign",
        "imaging.read",
        "imaging.write",
        "agenda.read",
        "agenda.write",
        "ai.use",
        "voice.use",
        "voice.clinical",
    ),
    "especialista": (
        "patients.read",
        "records.read",
        "records.write",
        "odontogram.read",
        "odontogram.write",
        "diagnosis.read",
        "diagnosis.write",
        "treatment.read",
        "treatment.write",
        "treatment.accept_budget",
        "documents.read",
        "documents.write",
        "documents.sign",
        "imaging.read",
        "imaging.write",
        "agenda.read",
        "agenda.write",
        "ai.use",
        "voice.use",
        "voice.clinical",
    ),
    "asistente": (
        "patients.read",
        "odontogram.read",
        "imaging.read",
        "imaging.write",
        "agenda.read",
    ),
    "recepcion": (
        "patients.read",
        "patients.write",
        "agenda.read",
        "agenda.write",
        "billing.read",
        "voice.use",
    ),
    "caja": (
        "patients.read",
        "billing.read",
        "billing.write",
        "reports.read",
    ),
    "demo": tuple(PERMISSIONS.keys()),
}
