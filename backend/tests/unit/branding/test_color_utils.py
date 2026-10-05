from app.modules.branding import color_utils


def test_contrast_ratio_black_on_white_is_maximum() -> None:
    assert color_utils.contrast_ratio("#000000", "#FFFFFF") == 21.0


def test_contrast_ratio_same_color_is_minimum() -> None:
    assert round(color_utils.contrast_ratio("#2BB3A3", "#2BB3A3"), 2) == 1.0


def test_contrast_ratio_is_symmetric() -> None:
    a = color_utils.contrast_ratio("#2BB3A3", "#F7FAFA")
    b = color_utils.contrast_ratio("#F7FAFA", "#2BB3A3")
    assert round(a, 4) == round(b, 4)


def test_suggest_contrasting_color_reaches_target_on_light_background() -> None:
    low_contrast_fg = "#EEEEEE"
    bg = "#FFFFFF"
    assert color_utils.contrast_ratio(low_contrast_fg, bg) < 4.5

    suggested = color_utils.suggest_contrasting_color(low_contrast_fg, bg)

    assert color_utils.contrast_ratio(suggested, bg) >= 4.5


def test_suggest_contrasting_color_reaches_target_on_dark_background() -> None:
    low_contrast_fg = "#333333"
    bg = "#000000"
    assert color_utils.contrast_ratio(low_contrast_fg, bg) < 4.5

    suggested = color_utils.suggest_contrasting_color(low_contrast_fg, bg)

    assert color_utils.contrast_ratio(suggested, bg) >= 4.5


def test_suggest_contrasting_color_is_noop_when_already_passing() -> None:
    assert color_utils.suggest_contrasting_color("#000000", "#FFFFFF") == "#000000"


def test_derive_hover_is_darker_than_primary() -> None:
    primary = "#2BB3A3"
    hover = color_utils.derive_hover(primary)
    assert color_utils.relative_luminance(
        color_utils.hex_to_rgb(hover)
    ) < color_utils.relative_luminance(color_utils.hex_to_rgb(primary))


def test_derive_soft_is_lighter_than_primary() -> None:
    primary = "#2BB3A3"
    soft = color_utils.derive_soft(primary)
    assert color_utils.relative_luminance(
        color_utils.hex_to_rgb(soft)
    ) > color_utils.relative_luminance(color_utils.hex_to_rgb(primary))


def test_is_valid_hex() -> None:
    assert color_utils.is_valid_hex("#2BB3A3") is True
    assert color_utils.is_valid_hex("2BB3A3") is False
    assert color_utils.is_valid_hex("#2BB3A") is False
    assert color_utils.is_valid_hex("not-a-color") is False
