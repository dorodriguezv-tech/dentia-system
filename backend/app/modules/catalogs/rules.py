"""Catalogo de tipos de catalogo administrables (Fase 12.2, Parte B1 de
docs/06_INSTRUCCIONES_CLAUDE_CODE_CORRECCIONES_Y_FASE13.md) y sus campos extra.

Antes de esta fase, estos catalogos vivian fijos en codigo (uno por modulo:
agenda/rules.py, odontogram/finding_catalog.py, etc.) y el administrador no podia
agregar ni desactivar un elemento sin pedir un cambio de codigo. Ahora viven en una
sola tabla por sucursal (`ClinicCatalogItem`), con los mismos valores por defecto que
antes (migracion de datos, nunca se recrean). El `code` interno nunca se edita (lo usan
la IA y los reportes); el `name` (etiqueta visible) y los campos de `extra` si.

"Metodos de pago" (B1) se deja fuera a proposito: `PaymentMethod` es un `Literal`
tipado en `billing/schemas.py` (igual que `TemplateCode` en documents), usado para
agrupar totales de corte de caja y el recibo en PDF -- volverlo editable en caliente
exigiria replantear esa logica sin un beneficio claro (una clinica dental casi nunca
cambia "efectivo/tarjeta/transferencia"). Si la clinica lo pide, es un cambio futuro
acotado, igual que "Procedimientos y precios" (ya es su propia tabla, `ProcedureCatalog`,
desde la Fase 7 -- se integra en la misma pantalla, pero no se duplica aqui) y
"Gabinetes"/"Sucursales" (ya son `agenda.Resource`/`iam.Clinic`, tablas propias).
"""

CATALOG_TYPES: tuple[str, ...] = (
    "appointment_type",
    "odontogram_finding",
    "diagnosis",
    "history_category",
    "condition_alert_keyword",
    "medication_alert_keyword",
)

CATALOG_TYPE_LABELS: dict[str, str] = {
    "appointment_type": "Tipos de consulta/cita",
    "odontogram_finding": "Hallazgos del odontograma",
    "diagnosis": "Diagnosticos",
    "history_category": "Categorias de antecedentes",
    "condition_alert_keyword": "Palabras clave de alerta (antecedentes)",
    "medication_alert_keyword": "Palabras clave de alerta (medicamentos)",
}

# Campos esperados en `extra` (JSONB) por tipo de catalogo -- documentado aqui, no
# forzado por un esquema estricto en la base (JSONB es deliberadamente flexible),
# para que agregar un campo nuevo a un tipo no exija una migracion de columnas.
EXTRA_FIELDS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "appointment_type": ("default_minutes", "color"),
    "odontogram_finding": ("symbol", "color", "requires_surface"),
    "diagnosis": (),
    "history_category": (),
    "condition_alert_keyword": ("alert_label",),
    "medication_alert_keyword": ("alert_label",),
}


def is_valid_catalog_type(catalog_type: str) -> bool:
    return catalog_type in CATALOG_TYPES
