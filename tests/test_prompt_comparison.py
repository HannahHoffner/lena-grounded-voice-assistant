"""Providerfreie Grenzen des echten Promptvergleichs."""

import asyncio
import json
from dataclasses import replace

import pytest

from app.config import load_settings
from app.formulation import FORMULATOR_SYSTEM_PROMPT
from app.prompt_comparison import (
    CANDIDATE_PROMPT, compare_one, load_frozen, prepare, review_packets, run, summarize,
)
from app.prompt_comparison_cases import comparison_cases
from app.providers.llm import BlabladorProvider, ProviderTimeoutError


@pytest.fixture
def settings():
    return replace(load_settings(), rewrite_provider="blablador",
                   blablador_base_url="https://example.invalid/v1",
                   blablador_api_key="test-comparison-secret", blablador_model="test-model")


def response(text="Nordpunkt bietet warme Mahlzeiten."):
    return {"model": "test-model", "choices": [{"message": {"content": json.dumps({
        "contract_version": "5", "language": "de", "sentences": [{
            "text": text, "claim_type": "service", "offer_id": "40",
            "fact_ids": ["f_0000000100000001", "f_0000000100000002"], "policy_ids": [],
        }], "card_ids": ["40"],
    })}}], "usage": {"total_tokens": 12, "unsafe_extra": "private"}}


def test_fixed_cases_cover_all_languages_and_frozen_splits():
    cases = comparison_cases()
    assert len(cases) == 60
    assert len({c["id"] for c in cases}) == 60
    assert {c["evidence"]["requested_language"] for c in cases} == {"de", "en", "pl", "ro", "ru"}
    assert sum(c["split"] == "holdout" for c in cases) == 20
    assert all(c["required"] and c["forbidden"] for c in cases)
    # Fresh objects: one call cannot mutate another arm's evidence.
    cases[0]["evidence"]["current_query"] = "changed"
    assert comparison_cases()[0]["evidence"]["current_query"] != "changed"


def test_prepare_is_offline_exclusive_and_tamper_evident(tmp_path):
    directory = tmp_path / "study"
    manifest = prepare(directory)
    assert manifest["expected_calls"] == {"development": 80, "holdout": 50}
    assert load_frozen(directory)[0] == manifest
    with pytest.raises(FileExistsError):
        prepare(directory)
    cases = json.loads((directory / "cases.json").read_text(encoding="utf-8"))
    cases[0]["evidence"]["current_query"] = "changed"
    (directory / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
    with pytest.raises(ValueError, match="cases_changed"):
        load_frozen(directory)


def test_prompt_tampering_is_rejected(tmp_path):
    directory = tmp_path / "study"
    prepare(directory)
    (directory / "prompts.json").write_text('{"baseline":"changed"}', encoding="utf-8")
    with pytest.raises(ValueError, match="prompts_changed"):
        load_frozen(directory)


def test_changed_source_and_repository_output_are_rejected(monkeypatch, tmp_path):
    directory = tmp_path / "study"
    prepare(directory)
    monkeypatch.setattr("app.prompt_comparison._source_hashes", lambda: {})
    with pytest.raises(ValueError, match="source_changed"):
        load_frozen(directory)
    monkeypatch.setattr("app.prompt_comparison.checkout_root", lambda: tmp_path)
    with pytest.raises(ValueError, match="outside_checkout"):
        prepare(tmp_path / "unsafe")
    assert not (tmp_path / "unsafe").exists()


def test_real_adapter_receives_identical_evidence_but_different_prompt(monkeypatch, settings):
    payloads = []
    async def post(self, payload):
        payloads.append(payload)
        return response()
    monkeypatch.setattr(BlabladorProvider, "_post", post)
    case = comparison_cases()[0]
    for arm, prompt in (("baseline", FORMULATOR_SYSTEM_PROMPT), ("candidate", CANDIDATE_PROMPT)):
        row = asyncio.run(compare_one(settings, prompt, case, arm, 1))
        assert row["gate_status"] == "accepted"
        assert row["raw_content"]
        assert row["usage"] == {"total_tokens": 12}
        assert settings.blablador_api_key not in json.dumps(row)
    assert payloads[0]["messages"][1] == payloads[1]["messages"][1]
    assert payloads[0]["messages"][0] != payloads[1]["messages"][0]
    assert payloads[0]["model"] == payloads[1]["model"]


def test_characterizes_unchecked_service_preserves_raw_draft(monkeypatch, settings):
    async def post(self, payload):
        return response("Nordpunkt bietet Wundversorgung an.")
    monkeypatch.setattr(BlabladorProvider, "_post", post)
    row = asyncio.run(compare_one(settings, CANDIDATE_PROMPT, comparison_cases()[0], "candidate", 1))
    assert row["gate_status"] == "accepted"
    assert "Wundversorgung" in row["raw_content"]
    assert not row.get("diagnostic_code")  # Lexical service support no longer gates.


def test_invalid_json_is_not_counted_as_semantic_gate_rejection(monkeypatch, settings):
    async def post(self, payload):
        return {"choices": [{"message": {"content": "not json"}}]}
    monkeypatch.setattr(BlabladorProvider, "_post", post)
    row = asyncio.run(compare_one(settings, CANDIDATE_PROMPT, comparison_cases()[0], "candidate", 1))
    assert row["gate_status"] == "failed"
    assert row["error_code"] == "formulator_invalid_json"
    assert row["raw_content"] == "not json"


def test_timeout_report_contains_no_free_exception_text(monkeypatch, settings):
    async def post(self, payload):
        raise ProviderTimeoutError("secret detail")
    monkeypatch.setattr(BlabladorProvider, "_post", post)
    row = asyncio.run(compare_one(settings, CANDIDATE_PROMPT, comparison_cases()[0], "candidate", 1))
    assert row["error_code"] == "formulator_timeout"
    assert row["raw_content"] is None
    assert "secret detail" not in json.dumps(row)


def test_missing_provider_stops_before_output_file(monkeypatch, tmp_path, settings):
    directory = tmp_path / "study"
    prepare(directory)
    monkeypatch.setattr("app.prompt_comparison.load_settings", lambda: replace(settings, blablador_api_key=None))
    with pytest.raises(ValueError, match="not_configured"):
        asyncio.run(run(directory, "development"))
    assert not (directory / "development.jsonl").exists()


@pytest.mark.parametrize("split,expected", [("development", 80), ("holdout", 50)])
def test_run_is_bounded_complete_and_never_overwrites(monkeypatch, tmp_path, settings, split, expected):
    calls = []
    async def post(self, payload):
        calls.append(payload)
        return response()
    monkeypatch.setattr(BlabladorProvider, "_post", post)
    monkeypatch.setattr("app.prompt_comparison.load_settings", lambda: settings)
    directory = tmp_path / "study"
    prepare(directory)
    summary = asyncio.run(run(directory, split))
    assert summary["completed"] is True
    assert summary["calls"] == len(calls) == expected
    rows = [json.loads(line) for line in (directory / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len({row["sample_id"] for row in rows}) == expected
    assert sum(row["arm"] == "candidate" for row in rows) == expected // 2
    with pytest.raises(FileExistsError):
        asyncio.run(run(directory, split))
    assert len(calls) == expected


def test_summary_needs_complete_explicit_reviews_and_distinguishes_false_rejections(tmp_path):
    row = {"sample_id": "a", "case_id": "meal_de", "arm": "candidate", "split": "development",
           "gate_status": "rejected", "raw_content": "draft"}
    for split, rows in (("development", [row]), ("holdout", [])):
        (tmp_path / f"{split}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    (tmp_path / "reviews.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        summarize(tmp_path)
    reviews = {"a": {"supported": True, "answers_question": True, "major_error": False,
                     "reviewer": "codex", "reason": "supported paraphrase"}}
    (tmp_path / "reviews.json").write_text(json.dumps(reviews), encoding="utf-8")
    result = summarize(tmp_path)
    assert result["development/candidate"]["supported_but_rejected"] == 1
    assert result["independent_human_review_complete"] is False
    (tmp_path / "cases.json").write_text(json.dumps(comparison_cases()), encoding="utf-8")
    packet = review_packets(tmp_path)[0]
    assert not {"arm", "gate_status"}.intersection(packet)
