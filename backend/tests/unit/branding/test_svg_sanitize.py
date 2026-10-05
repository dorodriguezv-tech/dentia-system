import pytest

from app.modules.branding.svg_sanitize import InvalidSvgError, sanitize_svg

VALID_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
<circle cx="5" cy="5" r="4" fill="#2BB3A3" />
</svg>"""

SVG_WITH_SCRIPT = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
<script>alert('xss')</script>
<circle cx="5" cy="5" r="4" fill="#2BB3A3" onclick="alert('xss')" />
</svg>"""

SVG_WITH_JS_URI = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
<a href="javascript:alert('xss')"><circle cx="5" cy="5" r="4" /></a>
</svg>"""


def test_valid_svg_passes_through() -> None:
    result = sanitize_svg(VALID_SVG)
    assert b"circle" in result


def test_script_tag_is_removed() -> None:
    result = sanitize_svg(SVG_WITH_SCRIPT)
    assert b"<script" not in result
    assert b"alert" not in result


def test_event_attribute_is_removed() -> None:
    result = sanitize_svg(SVG_WITH_SCRIPT)
    assert b"onclick" not in result


def test_javascript_uri_is_removed() -> None:
    result = sanitize_svg(SVG_WITH_JS_URI)
    assert b"javascript:" not in result


def test_invalid_xml_is_rejected() -> None:
    with pytest.raises(InvalidSvgError):
        sanitize_svg(b"not even xml")


def test_non_svg_root_is_rejected() -> None:
    with pytest.raises(InvalidSvgError):
        sanitize_svg(b"<html><body>hola</body></html>")
