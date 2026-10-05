from app.modules.encounters import rules


def test_draft_can_go_to_final() -> None:
    assert rules.can_transition("DRAFT", "FINAL") is True


def test_draft_can_be_cancelled() -> None:
    assert rules.can_transition("DRAFT", "CANCELLED") is True


def test_final_can_be_corrected() -> None:
    assert rules.can_transition("FINAL", "CORRECTED") is True


def test_final_can_be_cancelled() -> None:
    assert rules.can_transition("FINAL", "CANCELLED") is True


def test_final_cannot_go_back_to_draft() -> None:
    assert rules.can_transition("FINAL", "DRAFT") is False


def test_corrected_is_terminal() -> None:
    assert rules.can_transition("CORRECTED", "FINAL") is False
    assert rules.can_transition("CORRECTED", "CANCELLED") is False


def test_cancelled_is_terminal() -> None:
    assert rules.can_transition("CANCELLED", "DRAFT") is False


def test_only_draft_is_editable() -> None:
    assert rules.is_editable("DRAFT") is True
    assert rules.is_editable("FINAL") is False
    assert rules.is_editable("CORRECTED") is False
    assert rules.is_editable("CANCELLED") is False


def test_content_hash_is_deterministic() -> None:
    a = rules.compute_content_hash("s", "o", "a", "p", "free")
    b = rules.compute_content_hash("s", "o", "a", "p", "free")
    assert a == b


def test_content_hash_changes_with_content() -> None:
    a = rules.compute_content_hash("s", "o", "a", "p", "free")
    b = rules.compute_content_hash("s2", "o", "a", "p", "free")
    assert a != b


def test_content_hash_handles_none_fields() -> None:
    result = rules.compute_content_hash(None, None, None, None, "solo texto libre")
    assert isinstance(result, str) and len(result) == 64
