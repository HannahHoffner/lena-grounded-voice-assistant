"""Statische Integrationspruefungen der barrierearmen Dialogoberflaeche."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_clarification_uses_semantic_buttons_and_parallel_input_paths() -> None:
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    dialogue = (ROOT / "app" / "static" / "dialogue.js").read_text(encoding="utf-8")

    assert 'id="clarificationPanel"' in html
    assert 'aria-labelledby="clarificationPrompt"' in html
    assert 'role="group"' in html
    assert 'id="queryInput"' in html and 'id="micButton"' in html
    assert 'button.type = "button"' in dialogue
    assert 'button.textContent = choice.label' in dialogue
    assert 'button.setAttribute("aria-pressed"' in dialogue
    assert "if (this.busy" in dialogue
    assert "state.isSubmitting" in app
    assert "choice_values" in app and "dialog_id" in app


def test_technical_choice_values_are_never_rendered_as_chat_text() -> None:
    app = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    dialogue = (ROOT / "app" / "static" / "dialogue.js").read_text(encoding="utf-8")

    assert "question.textContent = turn.question" in app
    assert "choice.value" not in dialogue.split("textContent", 1)[1].split("dataset.choiceValue", 1)[0]
    assert 'dataset.choiceValue = choice.value' in dialogue
    assert "submitQuery(\"\", { dialogId, values })" in app


def test_language_change_preserves_session_and_relocalizes_open_dialog() -> None:
    app = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "const preserveSession = Boolean(state.sessionId)" in app
    assert "if (!preserveSession) resetView()" in app
    assert "/api/dialogue/copy?language=" in app
    assert "dialogueUI.relocalize" in app


def test_safety_response_has_non_colour_label_single_alert_and_map_reset() -> None:
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")

    assert 'id="answerText"' in html
    assert '"acute_risk", "acute_risk_clarification", "technical_fallback"' in app
    assert 'text().safetyHeading' in app
    assert 'resultView.setAttribute("aria-live", "off")' in app
    assert 'answerText.setAttribute("role", "alert")' in app
    assert 'byId("answerText").focus()' in app
    assert 'clearMap();' in app
    assert '.safety-result .answer-heading::before' in css
    assert 'content: "!"' in css
    assert "tel:112" not in app and "tel:112" not in html


def test_selected_cards_without_map_destination_remain_visible() -> None:
    app = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")

    assert "function resultItems(cards, mapData)" in app
    assert "destinationId === card.id" in app
    assert "destinationId.startsWith(`${card.id}:`)" in app
    assert "...unmappedCards.map(offerCardAsDestination)" in app
    assert "const items = resultItems(cards, mapData);" in app
