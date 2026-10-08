"""Ruta rapida (sin LLM) para las intenciones de navegacion de 13.2
(docs/05_ASISTENTE_DENTIA_VOZ_CONVERSACIONAL.md sec. 4.1 y 5): gramatica por
palabras clave/regex sobre el texto ya transcrito. Cubre lo mas frecuente segun
el diseno ("~80% de los casos"); lo que no reconoce cae en "no te entendi" por
ahora -- la ruta LLM (Ollama con el esquema de intenciones de la pantalla
actual) es trabajo de la 13.5, todavia no existe.

Solo funciones puras sobre texto: sin BD, sin IO, para poder probarlas
exhaustivamente (igual que app/ai/dental_parser.py).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.ai import dental_parser

_DESTINATIONS = {
    "agenda": "agenda",
    "odontograma": "odontograma",
    "expediente": "expediente",
    "tratamientos": "tratamientos",
    "tratamiento": "tratamientos",
    "imagenes": "imagenes",
    "inicio": "inicio",
    "pacientes": "pacientes",
    "consentimientos": "consentimientos",
}

_HELP_PHRASES = {"ayuda", "que puedo decir", "ayudame", "que sabes hacer"}
_REPEAT_PHRASES = {"repite", "repetir", "que dijiste", "como", "perdon"}
_SILENCE_PHRASES = {
    "silencio",
    "dentia silencio",
    "deja de escuchar",
    "calla",
    "callate",
    "guarda silencio",
}
_UNDO_PHRASES = {"deshaz", "deshazlo", "deshacer", "quita lo ultimo", "deshaz eso"}
_START_ENCOUNTER_RE = re.compile(
    r"\b(inicia|iniciar|empieza|empezar|comienza|comenzar)\b.*\b(consulta|atencion)\b"
)

# Fase 13.5 "Ruta LLM y dictado" (sec. 4.2 del diseno): "Dentia, dictado" ...
# "Dentia, fin del dictado" -- mientras dura, session.py deja de mandar cada
# frase a `match()` (ver `is_dictation_end`, revisada aparte en modo dictado).
_DICTATION_START_PHRASES = {"dictado", "modo dictado", "inicia el dictado", "empieza el dictado"}
_DICTATION_END_PHRASES = {
    "fin del dictado",
    "fin dictado",
    "termina el dictado",
    "termino el dictado",
    "ya termine",
    "ya termino",
}

# Sec. 3 del diseno: "Respuestas validas para confirmar... Para negar...".
# Coincidencia exacta sobre la frase completa (no por palabra suelta dentro de
# una frase larga): durante la cuenta regresiva (nivel 2) o la confirmacion
# explicita (nivel 3) Dentia sigue escuchando el consultorio, y una palabra
# como "no" dicha de paso en otra frase no deberia cancelar nada.
_CONFIRM_PHRASES = {"si", "correcto", "adelante", "confirmo", "ok"}
_CANCEL_PHRASES = {"no", "cancela", "cancelalo", "olvidalo", "espera", "alto"}

# Fase 13.3 "Captura en consulta": palabras/frases de hallazgo del odontograma
# -> codigo del catalogo (app/modules/odontogram/finding_catalog.py). Se
# revisan de la mas especifica a la mas generica para que "extraccion
# indicada" no quede atrapada por "extraccion" sola.
_FINDING_KEYWORDS: dict[str, str] = {
    "sano": "sano",
    "sana": "sano",
    "caries": "caries",
    "cariada": "caries",
    "cariado": "caries",
    "resina": "restauracion",
    "restauracion": "restauracion",
    "obturacion": "restauracion",
    "corona": "corona",
    "tratamiento de conducto": "endodoncia",
    "endodoncia": "endodoncia",
    "conducto": "endodoncia",
    "extraccion indicada": "extraccion_indicada",
    "indicada para extraccion": "extraccion_indicada",
    "ausente": "ausente",
    "extraida": "ausente",
    "extraido": "ausente",
    "perdida": "ausente",
    "implante": "implante",
    "protesis fija": "protesis_fija",
    "puente": "protesis_fija",
    "sellador": "sellador",
    "selladores": "sellador",
    "fractura": "fractura",
    "fracturada": "fractura",
    "fracturado": "fractura",
    "movilidad": "movilidad",
    "movil": "movilidad",
}
_FINDING_KEYWORDS_BY_LENGTH = sorted(_FINDING_KEYWORDS, key=len, reverse=True)

# Fase 13.4 "Diagnostico, plan y agenda" (C2 del doc 06), mitad clinica: a
# diferencia de agenda (anclas de palabra clave), diagnostico es texto libre
# por naturaleza (no un catalogo cerrado) -- solo se reconoce el VERBO que
# introduce la orden, el resto queda intacto para `diagnosis.text`. Revisados
# ANTES que `_match_hallazgo` (sec. de abajo): sin eso, "planea una resina en
# la 36" se confundiria con un hallazgo porque "resina" tambien es palabra
# clave de hallazgo (-> "restauracion").
_DIAGNOSTICO_RE = re.compile(r"^(?:pon\s+un\s+diagnostico\s+de\s+|diagnostico:?\s+)(?P<rest>.+)$")
_PROC_PLANEADO_RE = re.compile(
    r"^(?:procedimiento\s+planeado\s+|planea(?:r)?\s+|agrega\s+al\s+plan\s+)(?P<rest>.+)$"
)
_PROC_REALIZADO_RE = re.compile(
    r"^(?:procedimiento\s+realizado\s+|hice\s+|realice\s+|termine\s+(?:la\s+|el\s+)?)(?P<rest>.+)$"
)

# Fase 13.4 "Diagnostico, plan y agenda" (C2 del doc 06): agenda por voz para
# recepcion. Frases ancladas por palabras clave ("con", "el"/"al", "a las"),
# no una gramatica libre -- una frase fuera de este formato cae en "no te
# entendi" (la ruta LLM de la 13.5 es quien entendera fraseo libre).
_AGENDAR_RE = re.compile(r"^agenda(?:le)?\s+a\s+(?P<rest>.+)$")
_REPROGRAMAR_RE = re.compile(r"^(?:mueve|reprograma)\s+la\s+cita\s+de\s+(?P<rest>.+)$")
_CONFIRMAR_RE = re.compile(r"^confirma\s+la\s+cita\s+de\s+(?P<rest>.+)$")
_LLEGO_RE = re.compile(r"^lle[gj]o\s+(?P<patient>.+)$")

# Resto de C2 del doc 06 (recepcion, sin exigir `voice.clinical`): huecos
# libres, cancelar/no_show, lista de espera y alta rapida de paciente.
_HUECOS_LIBRES_RE = re.compile(
    r"\b(?:huecos?\s+libres?|horarios?\s+libres?|horarios?\s+disponibles?|"
    r"espacios?\s+disponibles?|cuando\s+hay\s+espacio|hay\s+espacio)\b"
)
_WEEK_ANCHOR_RE = re.compile(r"\besta\s+semana\b")
_CANCELAR_RE = re.compile(r"^cancela\s+la\s+cita\s+de\s+(?P<rest>.+)$")
_MOTIVO_RE = re.compile(r"\bmotivo:?\s+(?P<motivo>.+)$")
_NO_SHOW_PREFIX_RE = re.compile(
    r"^(?:marca\s+no\s+show\s+(?:a|de)\s+|no\s+(?:se\s+presento|llego)\s+)(?P<patient>.+)$"
)
_NO_SHOW_SUFFIX_RE = re.compile(r"^(?P<patient>.+?)\s+no\s+(?:se\s+presento|llego)$")
_LISTA_ESPERA_PRONOUN_PHRASES = {
    "agregala a la lista de espera",
    "agregalo a la lista de espera",
    "ponla en la lista de espera",
    "ponlo en la lista de espera",
    "agregala en la lista de espera",
}
_LISTA_ESPERA_RE = re.compile(
    r"^(?:agrega(?:le)?\s+a\s+|pon\s+a\s+)(?P<patient>.+?)\s+(?:a|en)\s+la\s+lista\s+de\s+espera$"
)
_LISTA_ESPERA_SUFFIX_RE = re.compile(r"^(?P<patient>.+?)\s+a\s+la\s+lista\s+de\s+espera$")
_ALTA_RAPIDA_RE = re.compile(
    r"^(?:registra(?:me)?\s+(?:a\s+)?(?:un\s+)?paciente\s+nuevo\s+|"
    r"da\s+de\s+alta\s+a\s+|dar\s+de\s+alta\s+a\s+|nuevo\s+paciente\s+)(?P<rest>.+)$"
)
_TELEFONO_RE = re.compile(r"\btelefono:?\s+(?P<phone>[\d\s]+)$")

_PROVIDER_ANCHOR_RE = re.compile(
    # Alternativas de la mas larga a la mas corta: "doctora"/"dra" antes que
    # "doctor"/"dr" para que no se coman solo el prefijo ("doctor" es un
    # prefijo literal de "doctora").
    r"\bcon\s+(?:el\s+doctor|la\s+doctora|doctora|doctor|dra|dr)?\s*"
)
# "el jueves"/"al jueves" consumen la palabra que los antecede; "mañana"/"hoy"
# no llevan ninguna palabra delante en el habla natural ("agenda a Juan Pérez
# MAÑANA a las 10"), por eso son un ancla de ancho cero (no consumen nada,
# solo marcan donde empieza la fecha).
_DATE_ANCHOR_RE = re.compile(r"\b(?:el|al)\s+|(?=\b(?:manana|hoy)\b)")
_TIME_ANCHOR_RE = re.compile(r"\ba las\s+")


def _segment_by_anchors(text: str, anchors: list[tuple[str, re.Pattern[str]]]) -> dict[str, str]:
    """Encuentra cada ancla (p.ej. "con", "el"/"al", "a las") y devuelve, por
    cada etiqueta, el texto entre esa ancla y la siguiente que aparezca (o el
    final). Lo que viene ANTES de la primera ancla queda en "_before" --
    normalmente el nombre del paciente.

    `anchors` es una lista ORDENADA por prioridad (la más específica
    primero): cada ancla se busca sobre una copia del texto donde ya se
    "enmascaró" (se sustituyó por espacios, sin mover posiciones) lo que
    consumieron las anclas anteriores -- así "con el doctor Gómez" no hace
    que el "el" de ahí se confunda también con el ancla de fecha ("el"/"al")."""
    working = text
    found: list[tuple[int, int, str]] = []
    for label, pattern in anchors:
        m = pattern.search(working)
        if m:
            found.append((m.start(), m.end(), label))
            working = working[: m.start()] + (" " * (m.end() - m.start())) + working[m.end() :]
    found.sort()

    segments: dict[str, str] = {"_before": text[: found[0][0]].strip() if found else text.strip()}
    for i, (_start, end, label) in enumerate(found):
        next_start = found[i + 1][0] if i + 1 < len(found) else len(text)
        segments[label] = text[end:next_start].strip()
    return segments


def _match_agendar_cita(text: str) -> FastMatch | None:
    m = _AGENDAR_RE.match(text)
    if not m:
        return None
    segments = _segment_by_anchors(
        m.group("rest"),
        [
            ("provider", _PROVIDER_ANCHOR_RE),
            ("date", _DATE_ANCHOR_RE),
            ("time", _TIME_ANCHOR_RE),
        ],
    )
    patient_query = segments["_before"]
    if not patient_query:
        return None
    return FastMatch(
        "agendar_cita",
        {
            "patient_query": patient_query,
            "date_text": segments.get("date", ""),
            "time_text": _format_time_text(segments.get("time", "")),
            "provider_query": segments.get("provider", ""),
            "full_text": text,
        },
    )


def _match_reprogramar_cita(text: str) -> FastMatch | None:
    m = _REPROGRAMAR_RE.match(text)
    if not m:
        return None
    segments = _segment_by_anchors(
        m.group("rest"), [("date", _DATE_ANCHOR_RE), ("time", _TIME_ANCHOR_RE)]
    )
    patient_query = segments["_before"]
    if not patient_query:
        return None
    return FastMatch(
        "reprogramar_cita",
        {
            "patient_query": patient_query,
            "date_text": segments.get("date", ""),
            "time_text": _format_time_text(segments.get("time", "")),
        },
    )


def _format_time_text(raw: str) -> str:
    """El ancla de hora (`_TIME_ANCHOR_RE`) consume "a las " al segmentar --
    se vuelve a anteponer para que `datetime_parse.extract_time_of_day`
    siempre reciba el mismo formato ("a las ...", vacio si no hubo hora)."""
    return f"a las {raw}" if raw else ""


def _match_confirmar_cita(text: str) -> FastMatch | None:
    m = _CONFIRMAR_RE.match(text)
    if not m:
        return None
    rest = m.group("rest").strip()
    time_match = re.match(r"^las\s+\d", rest)
    if time_match:
        return FastMatch("confirmar_cita", {"time_text": f"a {rest}", "patient_query": ""})
    return FastMatch("confirmar_cita", {"patient_query": rest, "time_text": ""})


def _match_registrar_llegada(text: str) -> FastMatch | None:
    m = _LLEGO_RE.match(text)
    if not m:
        return None
    return FastMatch("registrar_llegada", {"patient_query": m.group("patient").strip()})


def _match_huecos_libres(text: str) -> FastMatch | None:
    if not _HUECOS_LIBRES_RE.search(text):
        return None
    week_match = _WEEK_ANCHOR_RE.search(text)
    # Enmascara "esta semana" antes de buscar al profesional -- si no, el
    # ancla de proveedor (que toma todo hasta el final) se la come (mismo
    # criterio que `_segment_by_anchors` al enmascarar anclas ya consumidas).
    working = text[: week_match.start()] + text[week_match.end() :] if week_match else text
    segments = _segment_by_anchors(
        working, [("provider", _PROVIDER_ANCHOR_RE), ("date", _DATE_ANCHOR_RE)]
    )
    date_text = "esta semana" if week_match else segments.get("date", "")
    return FastMatch(
        "huecos_libres", {"provider_query": segments.get("provider", ""), "date_text": date_text}
    )


def _split_motivo(text: str) -> tuple[str, str]:
    """Separa "<cita>, motivo: <razon>" -- el motivo es siempre lo ultimo en la
    frase (sec. C2 del doc 06: "cancela la cita de las 12, motivo: enfermedad"),
    nunca al centro, asi que basta buscarlo desde el final."""
    m = _MOTIVO_RE.search(text)
    if not m:
        return text.strip().rstrip(","), ""
    return text[: m.start()].strip().rstrip(","), m.group("motivo").strip()


def _match_cancelar_cita(text: str) -> FastMatch | None:
    m = _CANCELAR_RE.match(text)
    if not m:
        return None
    target, motivo = _split_motivo(m.group("rest"))
    if re.match(r"^las\s+\d", target):
        return FastMatch(
            "cancelar_cita", {"time_text": f"a {target}", "patient_query": "", "reason": motivo}
        )
    return FastMatch("cancelar_cita", {"patient_query": target, "time_text": "", "reason": motivo})


def _match_no_show(text: str) -> FastMatch | None:
    m = _NO_SHOW_PREFIX_RE.match(text) or _NO_SHOW_SUFFIX_RE.match(text)
    if not m:
        return None
    patient = m.group("patient").strip()
    if not patient:
        return None
    return FastMatch("no_show", {"patient_query": patient})


def _match_lista_espera(text: str) -> FastMatch | None:
    if text in _LISTA_ESPERA_PRONOUN_PHRASES:
        return FastMatch("lista_espera", {"patient_query": ""})
    m = _LISTA_ESPERA_RE.match(text) or _LISTA_ESPERA_SUFFIX_RE.match(text)
    if not m:
        return None
    patient = m.group("patient").strip()
    if not patient:
        return None
    return FastMatch("lista_espera", {"patient_query": patient})


def _match_alta_rapida_paciente(text: str) -> FastMatch | None:
    m = _ALTA_RAPIDA_RE.match(text)
    if not m:
        return None
    rest = m.group("rest").strip()
    phone = ""
    phone_match = _TELEFONO_RE.search(rest)
    if phone_match:
        phone = re.sub(r"\s+", "", phone_match.group("phone"))
        rest = rest[: phone_match.start()].strip().rstrip(",")
    if not rest:
        return None
    return FastMatch("alta_rapida_paciente", {"patient_name": rest, "phone": phone})


@dataclass
class FastMatch:
    intent: str
    slots: dict[str, str] = field(default_factory=dict)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower().strip())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-z0-9 ]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def strip_wake_word(transcript: str) -> str:
    """Normaliza y quita el "Dentia" inicial si vino incluido -- la orden
    capturada despues de la activacion puede traerlo (misma frase: "Dentia,
    abre...") o no (el usuario hizo una pausa). Publica porque session.py
    tambien la usa para decidir si ya hay una orden de verdad o si el usuario
    solo dijo "Dentia" y se quedo calla(d)o."""
    text = _normalize(transcript)
    return re.sub(r"^dentia[, ]*", "", text).strip()


def match_confirmation(transcript: str) -> str | None:
    """Para cuando la sesion esta esperando "si"/"no" (nivel 3) o "cancela"
    durante la cuenta regresiva (nivel 2) -- sec. 3 del diseno. Se revisa
    ANTES que `match()` mientras hay una captura pendiente (ver session.py);
    deliberadamente no quita la palabra de activacion ("Dentia") porque en
    esta situacion el usuario normalmente no la repite."""
    text = _normalize(transcript)
    if text in _CANCEL_PHRASES:
        return "cancel"
    if text in _CONFIRM_PHRASES:
        return "confirm"
    return None


def is_dictation_end(transcript: str) -> bool:
    """Revisada aparte (no por `match()`): mientras `session.py` esta en modo
    dictado, cada frase se acumula como texto en vez de pasar por las
    intenciones normales -- esta es la unica que de verdad "significa algo"
    en ese modo. No quita la palabra de activacion a proposito, igual que
    `match_confirmation` -- en modo dictado tampoco se suele repetir "Dentia"."""
    return _normalize(transcript) in _DICTATION_END_PHRASES


def _match_finding_code(text: str) -> str | None:
    for keyword in _FINDING_KEYWORDS_BY_LENGTH:
        if re.search(rf"\b{re.escape(keyword)}\b", text):
            return _FINDING_KEYWORDS[keyword]
    return None


def _match_diagnostico(text: str) -> FastMatch | None:
    m = _DIAGNOSTICO_RE.match(text)
    if not m:
        return None
    rest = m.group("rest").strip()
    if not rest:
        return None
    teeth = dental_parser.extract_tooth_mentions(rest)
    return FastMatch("diagnostico", {"text": rest, "tooth_fdi": str(teeth[0]) if teeth else ""})


def _match_procedimiento(intent: str, rest: str) -> FastMatch | None:
    rest = rest.strip()
    if not rest:
        return None
    teeth = dental_parser.extract_tooth_mentions(rest)
    surfaces = dental_parser.extract_surfaces(rest)
    return FastMatch(
        intent,
        {
            "full_text": rest,
            "tooth_fdi": str(teeth[0]) if teeth else "",
            "surfaces": ",".join(surfaces),
        },
    )


def _match_procedimiento_planeado(text: str) -> FastMatch | None:
    m = _PROC_PLANEADO_RE.match(text)
    if not m:
        return None
    return _match_procedimiento("procedimiento_planeado", m.group("rest"))


def _match_procedimiento_realizado(text: str) -> FastMatch | None:
    m = _PROC_REALIZADO_RE.match(text)
    if not m:
        return None
    return _match_procedimiento("procedimiento_realizado", m.group("rest"))


def _match_hallazgo(text: str) -> FastMatch | None:
    teeth = dental_parser.extract_tooth_mentions(text)
    if not teeth:
        return None
    finding_code = _match_finding_code(text)
    if finding_code is None:
        return None
    surfaces = dental_parser.extract_surfaces(text)
    return FastMatch(
        "hallazgo",
        {
            "tooth_fdi": str(teeth[0]),
            "finding_code": finding_code,
            "surfaces": ",".join(surfaces),
        },
    )


def match(transcript: str) -> FastMatch | None:
    text = strip_wake_word(transcript)
    if not text:
        return None

    if text in _HELP_PHRASES:
        return FastMatch("ayuda")
    if text in _REPEAT_PHRASES:
        return FastMatch("repetir")
    if text in _SILENCE_PHRASES:
        return FastMatch("silencio")
    if text in _UNDO_PHRASES:
        return FastMatch("deshacer")
    if _START_ENCOUNTER_RE.search(text):
        return FastMatch("iniciar_consulta")
    if text in _DICTATION_START_PHRASES:
        return FastMatch("modo_dictado")

    for agenda_matcher in (
        _match_agendar_cita,
        _match_reprogramar_cita,
        _match_confirmar_cita,
        _match_registrar_llegada,
        _match_huecos_libres,
        _match_cancelar_cita,
        _match_no_show,
        _match_lista_espera,
        _match_alta_rapida_paciente,
    ):
        agenda_match = agenda_matcher(text)
        if agenda_match is not None:
            return agenda_match

    # ANTES que hallazgo (ver comentario junto a los regex): "planea una
    # resina en la 36" no debe confundirse con un hallazgo de odontograma.
    for clinical_matcher in (
        _match_diagnostico,
        _match_procedimiento_planeado,
        _match_procedimiento_realizado,
    ):
        clinical_match = clinical_matcher(text)
        if clinical_match is not None:
            return clinical_match

    hallazgo_match = _match_hallazgo(text)
    if hallazgo_match is not None:
        return hallazgo_match

    if re.search(r"\b(alergias|alertas)\b", text) and re.search(
        r"\b(tiene|hay|lee|leeme|dime|cuales)\b", text
    ):
        return FastMatch("leer_alertas")

    if (
        re.search(r"\bcitas?\b.*\bhoy\b", text)
        or "quien sigue" in text
        or "que citas tengo" in text
    ):
        return FastMatch("citas_hoy")

    # "ir_a" se revisa antes que "abrir_expediente": ambas aceptan "abre..." como
    # disparador ("abre la agenda" vs "abre el expediente de Juan Perez"), pero
    # "ir_a" solo reconoce un conjunto cerrado de pantallas -- si el destino no es
    # una de ellas, cae a "abrir_expediente" tratandolo como un nombre.
    match_ir = re.match(
        r"^(ve|vete|vamos|anda|ir|abre|muestra)"
        r"\s+(a\s+)?(la\s+|el\s+|los\s+|al\s+)?(?P<dest>[a-z]+)$",
        text,
    )
    if match_ir:
        destino = _DESTINATIONS.get(match_ir.group("dest"))
        if destino:
            return FastMatch("ir_a", {"destino": destino})

    if text in _DESTINATIONS:
        return FastMatch("ir_a", {"destino": _DESTINATIONS[text]})

    match_abrir = re.match(
        r"^(abre|abreme|busca|abrir|buscar)"
        r"(\s+(el\s+)?expediente\s+de|\s+la\s+ficha\s+de|\s+a)?\s+(?P<query>.+)$",
        text,
    )
    if match_abrir and match_abrir.group("query"):
        return FastMatch("abrir_expediente", {"query": match_abrir.group("query").strip()})

    return None
