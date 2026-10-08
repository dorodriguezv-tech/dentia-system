"""`ScreenContext` (13.2 "Navegacion", sec. 6 del diseno): lo que el cliente manda
cada vez que cambia de pantalla (mensaje `context` del WebSocket, ya aceptado y
ignorado desde 13.1). Dentia lo usa para saber de que paciente/atencion se habla
sin que cada orden tenga que repetirlo ("lee las alertas" sin decir el nombre).
"""

from dataclasses import dataclass


@dataclass
class ScreenContext:
    route: str | None = None
    patient_id: str | None = None
    encounter_id: str | None = None
    tab: str | None = None

    @classmethod
    def from_message(cls, payload: dict[str, object]) -> "ScreenContext":
        def _str_or_none(value: object) -> str | None:
            return str(value) if value is not None else None

        return cls(
            route=_str_or_none(payload.get("route")),
            patient_id=_str_or_none(payload.get("patient_id")),
            encounter_id=_str_or_none(payload.get("encounter_id")),
            tab=_str_or_none(payload.get("tab")),
        )
