from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app.config import load_settings
from app.kb import KnowledgeBase
from app.maps import MapBuilder
from app.models import Language, QueryAnswerResponse, QueryRequest
from app.providers.rewrite import create_rewrite_provider
from app.retrieval import normalize_text
from app.sessions import SessionManager, SessionStore
from app.temporal import build_temporal_context


@dataclass(slots=True)
class TurnCheck:
    name: str
    passed: bool
    detail: str


def _load_cases(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(value: str) -> str:
    return normalize_text(value or "")


def _contains_any(answer_text: str, values: list[str]) -> bool:
    normalized_answer = _normalize(answer_text)
    return any(_normalize(value) in normalized_answer for value in values)


def _contains_all(answer_text: str, values: list[str]) -> bool:
    normalized_answer = _normalize(answer_text)
    return all(_normalize(value) in normalized_answer for value in values)


REDIRECT_NEEDLES = [
    "App herunterladen",
    "laden Sie die App herunter",
    "nutzen Sie die App",
    "Website besuchen",
    "auf der Website nachsehen",
    "online suchen",
    "Google Maps",
    "im Internet suchen",
    "die App zeigt",
    "finden Sie online",
    "finden Sie in der App",
    "download the app",
    "use the app",
    "check the website",
    "search online",
    "use Google Maps",
    "the app will show",
    "find it online",
]


def _is_concrete_page(page_id: str, kb: KnowledgeBase) -> bool:
    if not page_id:
        return False
    try:
        page = kb.get_page(page_id)
    except KeyError:
        return False
    if page.service_type == "service_catalog" or page.entity_kind == "service_program":
        return False
    return bool(page.address or (page.latitude is not None and page.longitude is not None))


def _concrete_page_ids(page_ids: list[str], kb: KnowledgeBase) -> list[str]:
    return [page_id for page_id in page_ids if _is_concrete_page(page_id, kb)]


def _geocoded_page_ids(page_ids: list[str], kb: KnowledgeBase) -> list[str]:
    geocoded: list[str] = []
    for page_id in page_ids:
        try:
            page = kb.get_page(page_id)
        except KeyError:
            continue
        if page.address and page.latitude is not None and page.longitude is not None:
            geocoded.append(page_id)
    return geocoded


def _answer_mentions_concrete_page(answer_text: str, page_ids: list[str], kb: KnowledgeBase) -> bool:
    for page_id in page_ids:
        try:
            page = kb.get_page(page_id)
        except KeyError:
            continue
        values = [page.title]
        if page.address:
            values.append(page.address)
        if _contains_any(answer_text, values):
            return True
    return False


def _hash_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _top_family(page_id: str | None, kb: KnowledgeBase) -> str | None:
    if not page_id:
        return None
    try:
        page = kb.get_page(page_id)
    except KeyError:
        return None
    return page.title.split(" - ", 1)[0].strip()


def _page_field_values(page_id: str | None, field: str, kb: KnowledgeBase) -> list[str]:
    if not page_id:
        return []
    try:
        page = kb.get_page(page_id)
    except KeyError:
        return []
    if field == "title":
        return [page.title]
    if field == "address":
        return [page.address] if page.address else []
    if field == "phone":
        return [page.phone] if page.phone else []
    if field == "email":
        return [page.email] if page.email else []
    if field == "opening_hours":
        return list(page.opening_hours)
    if field == "eligibility":
        return [page.eligibility] if page.eligibility else []
    return []


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return round(ordered[index], 1)


def _evaluate_turn(
    *,
    expect: dict[str, Any],
    actual: dict[str, Any],
    previous_turn: dict[str, Any] | None,
    kb: KnowledgeBase,
) -> list[TurnCheck]:
    checks: list[TurnCheck] = []
    if not expect:
        return checks

    if "status_in" in expect:
        checks.append(
            TurnCheck(
                name="status",
                passed=actual["status"] in expect["status_in"],
                detail=f"expected {expect['status_in']}, got {actual['status']}",
            )
        )
    if "session_event" in expect:
        checks.append(
            TurnCheck(
                name="session_event",
                passed=actual["session_event"] == expect["session_event"],
                detail=f"expected {expect['session_event']}, got {actual['session_event']}",
            )
        )
    if "same_session_as_previous" in expect and previous_turn:
        checks.append(
            TurnCheck(
                name="same_session_as_previous",
                passed=(actual["session_id"] == previous_turn["session_id"]) == bool(expect["same_session_as_previous"]),
                detail=f"previous={previous_turn['session_id']} current={actual['session_id']}",
            )
        )
    if "new_session_after_previous" in expect and previous_turn:
        checks.append(
            TurnCheck(
                name="new_session_after_previous",
                passed=(actual["session_id"] != previous_turn["session_id"]) == bool(expect["new_session_after_previous"]),
                detail=f"previous={previous_turn['session_id']} current={actual['session_id']}",
            )
        )
    if "top_page_in" in expect:
        checks.append(
            TurnCheck(
                name="top_page_in",
                passed=actual["top_page_id"] in expect["top_page_in"],
                detail=f"expected one of {expect['top_page_in']}, got {actual['top_page_id']}",
            )
        )
    if "top_page_prefixes" in expect:
        checks.append(
            TurnCheck(
                name="top_page_prefixes",
                passed=any((actual["top_page_id"] or "").startswith(prefix) for prefix in expect["top_page_prefixes"]),
                detail=f"expected prefixes {expect['top_page_prefixes']}, got {actual['top_page_id']}",
            )
        )
    if "top_page_not_equals_previous" in expect and previous_turn:
        checks.append(
            TurnCheck(
                name="top_page_not_equals_previous",
                passed=(actual["top_page_id"] != previous_turn["top_page_id"]) == bool(expect["top_page_not_equals_previous"]),
                detail=f"previous={previous_turn['top_page_id']} current={actual['top_page_id']}",
            )
        )
    if "top_page_not_in" in expect:
        checks.append(
            TurnCheck(
                name="top_page_not_in",
                passed=actual["top_page_id"] not in expect["top_page_not_in"],
                detail=f"forbidden={expect['top_page_not_in']} current={actual['top_page_id']}",
            )
        )
    if "retrieved_page_count" in expect:
        checks.append(
            TurnCheck(
                name="retrieved_page_count",
                passed=len(actual["retrieved_page_ids"]) == expect["retrieved_page_count"],
                detail=f"expected {expect['retrieved_page_count']}, got {len(actual['retrieved_page_ids'])}",
            )
        )
    if "answer_contains_any" in expect:
        checks.append(
            TurnCheck(
                name="answer_contains_any",
                passed=_contains_any(actual["answer_text"], expect["answer_contains_any"]),
                detail=f"expected any of {expect['answer_contains_any']}",
            )
        )
    if "answer_contains_all" in expect:
        checks.append(
            TurnCheck(
                name="answer_contains_all",
                passed=_contains_all(actual["answer_text"], expect["answer_contains_all"]),
                detail=f"expected all of {expect['answer_contains_all']}",
            )
        )
    if "answer_not_contains" in expect:
        checks.append(
            TurnCheck(
                name="answer_not_contains",
                passed=not _contains_any(actual["answer_text"], expect["answer_not_contains"]),
                detail=f"forbidden any of {expect['answer_not_contains']}",
            )
        )
    if expect.get("must_not_redirect_to_app"):
        checks.append(
            TurnCheck(
                name="must_not_redirect_to_app",
                passed=not _contains_any(actual["answer_text"], REDIRECT_NEEDLES),
                detail="answer must not redirect to external apps, websites, online search, or maps",
            )
        )
    concrete_ids = _concrete_page_ids(actual["retrieved_page_ids"], kb)
    if expect.get("requires_concrete_location") and actual["status"] in {"ok", "weak_match"}:
        checks.append(
            TurnCheck(
                name="requires_concrete_location",
                passed=bool(concrete_ids),
                detail=f"concrete retrieved pages={concrete_ids}",
            )
        )
    if expect.get("must_include_concrete_location_if_available") and concrete_ids:
        checks.append(
            TurnCheck(
                name="must_include_concrete_location_if_available",
                passed=_answer_mentions_concrete_page(actual["answer_text"], concrete_ids, kb),
                detail=f"expected answer to mention one of {concrete_ids}",
            )
        )
    geocoded_ids = _geocoded_page_ids(actual["retrieved_page_ids"], kb)
    if expect.get("must_include_map_targets_if_geo_available") and geocoded_ids:
        map_ids = set(actual.get("map_destination_ids") or [])
        checks.append(
            TurnCheck(
                name="must_include_map_targets_if_geo_available",
                passed=bool(map_ids & set(geocoded_ids)),
                detail=f"geocoded={geocoded_ids} map_destinations={sorted(map_ids)}",
            )
        )
    if "must_ground_fields" in expect:
        for field in expect["must_ground_fields"]:
            values = _page_field_values(actual["top_page_id"], field, kb)
            checks.append(
                TurnCheck(
                    name=f"must_ground_{field}",
                    passed=bool(values) and _contains_any(actual["answer_text"], values),
                    detail=f"expected supported {field} from {actual['top_page_id']}",
                )
            )
    if "must_not_invent" in expect:
        checks.append(
            TurnCheck(
                name="must_not_invent_sensitive_facts",
                passed=actual.get("validation_error") in {None, ""},
                detail=f"validation_error={actual.get('validation_error')}",
            )
        )
    if "different_family_from_previous" in expect and previous_turn:
        checks.append(
            TurnCheck(
                name="different_family_from_previous",
                passed=(_top_family(actual["top_page_id"], kb) != _top_family(previous_turn["top_page_id"], kb)) == bool(expect["different_family_from_previous"]),
                detail=f"previous_family={_top_family(previous_turn['top_page_id'], kb)} current_family={_top_family(actual['top_page_id'], kb)}",
            )
        )
    return checks


async def _run_case(
    *,
    case: dict[str, Any],
    provider_name: str,
    model_name: str,
    kb: KnowledgeBase,
    settings,
) -> dict[str, Any]:
    provider = create_rewrite_provider(
        provider_name,
        ollama_url=settings.ollama_url,
        ollama_model=model_name,
        ollama_timeout_seconds=settings.ollama_timeout_seconds,
        minimum_match_threshold=settings.minimum_match_threshold,
        weak_match_threshold=settings.weak_match_threshold,
        clarification_gap_threshold=settings.clarification_gap_threshold,
        system_prompt_path=settings.system_prompt_path,
        llm_base_url=settings.llm_base_url,
        llm_api_key=settings.llm_api_key,
        llm_model=model_name,
        llm_timeout_seconds=settings.llm_timeout_seconds,
        llm_max_tokens=settings.llm_max_tokens,
        llm_temperature=settings.llm_temperature,
        llm_fallback_provider=settings.llm_fallback_provider,
    )

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"lena-eval-{case['case_id']}-") as tmpdir:
        session_store = SessionStore(Path(tmpdir) / "sessions.json")
        session_manager = SessionManager(session_store, kb, timeout_seconds=settings.session_timeout_seconds)
        current_session_id: str | None = None
        current_time = datetime(2026, 4, 21, 12, 0, tzinfo=UTC)

        for turn_index, turn in enumerate(case["turns"]):
            payload = QueryRequest(
                transcript=turn["transcript"],
                language=Language(turn["language"]),
                session_id=current_session_id,
            )
            resolution = session_manager.prepare_request(payload, now=current_time)
            temporal_context = build_temporal_context(now=current_time, timezone=settings.timezone)
            started = time.perf_counter()
            answer = await provider.answer(
                payload.transcript,
                payload.language,
                kb,
                conversation_context=resolution.context,
                temporal_context=temporal_context,
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            response = QueryAnswerResponse(
                answer_text=answer.answer_text,
                status=answer.status,
                weak_match=answer.weak_match,
                clarification_needed=answer.clarification_needed,
                clarification_question=answer.clarification_question,
                retrieved_page_ids=answer.retrieved_page_ids,
                map_data=MapBuilder(settings).build_for_answer(answer, kb),
                provider=provider.name,
                model=model_name,
                session_id=resolution.session.session_id,
                session_status=resolution.session.status,
                session_event=resolution.session_event,
                session_message=resolution.session_message,
            )
            updated_session = session_manager.record_turn(
                resolution.session,
                payload,
                response,
                resolution.context,
                now=current_time,
            )
            current_session_id = updated_session.session_id
            actual = {
                "turn_index": turn_index,
                "transcript": turn["transcript"],
                "language": turn["language"],
                "resolved_transcript": getattr(provider, "last_resolved_transcript", None),
                "status": response.status,
                "session_id": response.session_id,
                "session_event": response.session_event.value,
                "session_status": response.session_status.value,
                "retrieved_page_ids": response.retrieved_page_ids,
                "top_page_id": response.retrieved_page_ids[0] if response.retrieved_page_ids else None,
                "map_destination_ids": [destination.page_id for destination in response.map_data.destinations] if response.map_data else [],
                "answer_text": response.answer_text,
                "answer_source": getattr(provider, "last_answer_source", "unknown"),
                "fallback": "fallback" in str(getattr(provider, "last_answer_source", "")),
                "evidence_hash": _hash_text(getattr(provider, "last_evidence_context", "")),
                "evidence_context": getattr(provider, "last_evidence_context", ""),
                "prompt_hash": getattr(provider, "last_prompt_hash", None),
                "system_prompt_hash": getattr(provider, "last_system_prompt_hash", None),
                "user_prompt_hash": getattr(provider, "last_user_prompt_hash", None),
                "validation_error": getattr(provider, "last_validation_error", None),
                "provider_error": getattr(provider, "last_provider_error", None),
                "temporal_context": temporal_context.model_dump(),
                "latency_ms": latency_ms,
            }
            previous_turn = results[-1]["actual"] if results else None
            checks = _evaluate_turn(expect=turn.get("expect", {}), actual=actual, previous_turn=previous_turn, kb=kb)
            results.append(
                {
                    "turn_index": turn_index,
                    "manual_review_only": bool(case.get("manual_review_only", False)),
                    "expect": turn.get("expect", {}),
                    "actual": actual,
                    "checks": [asdict(check) for check in checks],
                    "pass": all(check.passed for check in checks) if checks else True,
                }
            )
            current_time += timedelta(seconds=turn.get("advance_seconds", 30))

    auto_turns = [turn for turn in results if not turn["manual_review_only"]]
    auto_checks = [check for turn in auto_turns for check in turn["checks"]]
    auto_passed = sum(1 for check in auto_checks if check["passed"])
    auto_total = len(auto_checks)
    return {
        "case_id": case["case_id"],
        "case_type": case.get("case_type", "general"),
        "description": case.get("description", ""),
        "manual_review_only": bool(case.get("manual_review_only", False)),
        "manual_review_focus": case.get("manual_review_focus", []),
        "turns": results,
        "auto_checks_passed": auto_passed,
        "auto_checks_total": auto_total,
        "pass": all(turn["pass"] for turn in auto_turns) if auto_turns else True,
    }


async def _evaluate_models(models: list[str], dataset_path: Path, provider_name: str) -> dict[str, Any]:
    settings = load_settings()
    kb = KnowledgeBase(settings.published_root)
    dataset = _load_cases(dataset_path)
    cases = dataset["cases"]
    summary: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": dataset_path.as_posix(),
        "kb_version": kb.dataset.manifest.kb_version,
        "system_prompt_path": settings.system_prompt_path.as_posix(),
        "provider": provider_name,
        "scoring_rubric": {
            "automated": [
                "status/session/retrieval expectations",
                "required grounded fields",
                "sensitive-fact validation errors",
            ],
            "manual": [
                "output language correctness",
                "plain-language clarity",
                "unsupported elaboration",
                "sensitive-question behavior",
            ],
        },
        "models": {},
    }
    for model_name in models:
        case_results: list[dict[str, Any]] = []
        for case in cases:
            case_results.append(await _run_case(case=case, provider_name=provider_name, model_name=model_name, kb=kb, settings=settings))
        auto_checks_passed = sum(case["auto_checks_passed"] for case in case_results)
        auto_checks_total = sum(case["auto_checks_total"] for case in case_results)
        answer_sources: dict[str, int] = {}
        status_distribution: dict[str, int] = {}
        validation_errors: dict[str, int] = {}
        provider_errors: dict[str, int] = {}
        latencies: list[float] = []
        prompt_hashes: set[str] = set()
        evidence_hashes: set[str] = set()
        for case in case_results:
            for turn in case["turns"]:
                source = turn["actual"]["answer_source"]
                answer_sources[source] = answer_sources.get(source, 0) + 1
                status = str(turn["actual"]["status"])
                status_distribution[status] = status_distribution.get(status, 0) + 1
                validation_error = turn["actual"].get("validation_error")
                if validation_error:
                    validation_errors[validation_error] = validation_errors.get(validation_error, 0) + 1
                provider_error = turn["actual"].get("provider_error")
                if provider_error:
                    provider_errors[provider_error] = provider_errors.get(provider_error, 0) + 1
                prompt_hash = turn["actual"].get("prompt_hash")
                if prompt_hash:
                    prompt_hashes.add(prompt_hash)
                evidence_hashes.add(turn["actual"].get("evidence_hash", ""))
                latencies.append(turn["actual"]["latency_ms"])
        summary["models"][model_name] = {
            "auto_checks_passed": auto_checks_passed,
            "auto_checks_total": auto_checks_total,
            "auto_score_percent": round((auto_checks_passed / auto_checks_total) * 100, 1) if auto_checks_total else 0.0,
            "median_latency_ms": _percentile(latencies, 0.5),
            "p95_latency_ms": _percentile(latencies, 0.95),
            "successful_responses": answer_sources.get("llm", 0) + answer_sources.get("template", 0) + answer_sources.get("guardrail", 0),
            "fallback_responses": sum(count for source, count in answer_sources.items() if "fallback" in source),
            "provider_error_count": sum(provider_errors.values()),
            "status_distribution": status_distribution,
            "answer_sources": answer_sources,
            "validation_errors": validation_errors,
            "provider_errors": provider_errors,
            "prompt_hash_count": len(prompt_hashes),
            "evidence_hash_count": len(evidence_hashes),
            "cases": case_results,
        }
    return summary


def _render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# LENA Model Evaluation",
        "",
        f"- Generated: {summary['generated_at']}",
        f"- KB version: {summary['kb_version']}",
        f"- Dataset: `{summary['dataset']}`",
        f"- System prompt: `{summary['system_prompt_path']}`",
        "",
    ]
    for model_name, result in summary["models"].items():
        lines.extend(
            [
                f"## {model_name}",
                "",
                f"- Automated score: {result['auto_checks_passed']}/{result['auto_checks_total']} ({result['auto_score_percent']}%)",
                f"- Median latency: {result['median_latency_ms']} ms",
                f"- p95 latency: {result['p95_latency_ms']} ms",
                f"- Successful responses: {result['successful_responses']}",
                f"- Fallback responses: {result['fallback_responses']}",
                f"- Provider errors: {result['provider_error_count']}",
                f"- Status distribution: {json.dumps(result['status_distribution'], ensure_ascii=False)}",
                f"- Answer sources: {json.dumps(result['answer_sources'], ensure_ascii=False)}",
                f"- Validation errors: {json.dumps(result['validation_errors'], ensure_ascii=False)}",
                f"- Provider errors by type: {json.dumps(result['provider_errors'], ensure_ascii=False)}",
                f"- Prompt hashes observed: {result['prompt_hash_count']}",
                f"- Evidence hashes observed: {result['evidence_hash_count']}",
                "",
                "| Case | Auto pass | Source | Latency | Key output |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        for case in result["cases"]:
            final_turn = case["turns"][-1]["actual"]
            key_output = final_turn["answer_text"].replace("\n", " ")
            if len(key_output) > 140:
                key_output = key_output[:137] + "..."
            lines.append(
                f"| `{case['case_id']}` | `{case['pass']}` | `{final_turn['answer_source']}` | "
                f"{final_turn['latency_ms']} | {key_output} |"
            )
        lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate grounded LENA rewrite providers and models.")
    parser.add_argument("--dataset", default="data/evals/assistant_eval_cases.json", help="Path to evaluation dataset JSON.")
    parser.add_argument("--provider", choices=["ollama", "template", "openai_compatible", "blablador"], default="ollama", help="Answer provider to evaluate.")
    parser.add_argument("--models", nargs="+", default=["translategemma:4b", "qwen3:4b"], help="Model names or provider aliases to evaluate.")
    parser.add_argument("--output-dir", default="data/evals/results", help="Directory for JSON and Markdown results.")
    args = parser.parse_args()

    dataset_path = (APP_ROOT / args.dataset).resolve()
    output_dir = (APP_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    models = args.models
    if args.provider == "template" and args.models == ["translategemma:4b", "qwen3:4b"]:
        models = ["template"]
    if args.provider == "blablador" and args.models == ["translategemma:4b", "qwen3:4b"]:
        models = ["alias-fast", "alias-large", "alias-huge"]
    summary = await _evaluate_models(models, dataset_path, args.provider)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    stem = output_dir / f"model-eval-{timestamp}"
    (stem.with_suffix(".json")).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    jsonl_rows: list[str] = []
    for model_name, result in summary["models"].items():
        for case in result["cases"]:
            for turn in case["turns"]:
                jsonl_rows.append(
                    json.dumps(
                        {
                            "generated_at": summary["generated_at"],
                            "provider": summary["provider"],
                            "model": model_name,
                            "case_id": case["case_id"],
                            **turn["actual"],
                            "checks": turn["checks"],
                            "pass": turn["pass"],
                            "manual_review_only": turn["manual_review_only"],
                        },
                        ensure_ascii=False,
                    )
                )
    stem.with_suffix(".jsonl").write_text("\n".join(jsonl_rows) + ("\n" if jsonl_rows else ""), encoding="utf-8")
    (stem.with_suffix(".md")).write_text(_render_markdown(summary), encoding="utf-8")

    printable_summary = json.dumps(summary, ensure_ascii=False, indent=2)
    try:
        print(printable_summary)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(printable_summary.encode("utf-8", errors="replace"))
        sys.stdout.buffer.write(b"\n")
    print(f"\nSaved results to {stem.with_suffix('.json')}")
    print(f"Saved JSONL rows to {stem.with_suffix('.jsonl')}")
    print(f"Saved report to {stem.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
