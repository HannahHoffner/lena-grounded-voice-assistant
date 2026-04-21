from __future__ import annotations

import json
from pathlib import Path


def test_eval_dataset_has_unique_case_ids() -> None:
    dataset_path = Path(__file__).resolve().parents[1] / "data" / "evals" / "assistant_eval_cases.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    case_ids = [case["case_id"] for case in dataset["cases"]]

    assert case_ids
    assert len(case_ids) == len(set(case_ids))
    assert any(case.get("case_type") == "weak_match_probe" for case in dataset["cases"])
