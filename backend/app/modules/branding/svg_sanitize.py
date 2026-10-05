"""Saneado de SVG subido como logo: sin <script> ni atributos de evento (onclick, etc.).

Usa xml.etree (stdlib) en vez de una libreria de parseo XML externa para no sumar una
dependencia nueva solo para esto; es un saneado enfocado, no un parser XML de proposito
general.
"""

import xml.etree.ElementTree as ET

_SVG_NS = "http://www.w3.org/2000/svg"
_XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", _SVG_NS)
ET.register_namespace("xlink", _XLINK_NS)

_DISALLOWED_TAGS = {
    f"{{{_SVG_NS}}}script",
    f"{{{_SVG_NS}}}foreignObject",
    f"{{{_SVG_NS}}}style",
    "script",
    "foreignObject",
    "style",
}

_DISALLOWED_ATTRS = {"style"}


class InvalidSvgError(ValueError):
    pass


def _is_event_attr(name: str) -> bool:
    local = name.split("}")[-1]
    return local.lower().startswith("on")


def _has_script_uri(value: str) -> bool:
    return value.strip().lower().startswith("javascript:")


def sanitize_svg(data: bytes) -> bytes:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise InvalidSvgError("El archivo no es un SVG valido") from exc

    if root.tag not in (f"{{{_SVG_NS}}}svg", "svg"):
        raise InvalidSvgError("El archivo no es un SVG valido")

    for element in list(root.iter()):
        if element.tag in _DISALLOWED_TAGS:
            _remove_element(root, element)
            continue

        for attr_name in list(element.attrib):
            value = element.attrib[attr_name]
            local_name = attr_name.split("}")[-1]
            if (
                _is_event_attr(attr_name)
                or _has_script_uri(value)
                or local_name in _DISALLOWED_ATTRS
            ):
                del element.attrib[attr_name]

    result: bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return result


def _remove_element(root: ET.Element, target: ET.Element) -> None:
    for parent in root.iter():
        if target in list(parent):
            parent.remove(target)
            return
