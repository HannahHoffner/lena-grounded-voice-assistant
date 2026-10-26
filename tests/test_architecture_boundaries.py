"""Ausführbarer Schichtenvertrag: Datenbasis, Fachregeln, Faktenprüfung, LLM.

Die Faktenprüfung darf weder den Modellanbieter noch die Wissensbasis,
Kandidatenregeln, Sessions oder die Orchestrierung kennen. Sie bewertet
ausschließlich eine Modellantwort gegen ein bereits gebildetes Evidence-Paket.
Fachregeln entscheiden vor jeder Formulierung und kennen weder LLM-Adapter noch
Faktenprüfung. Die Datenbasis kennt keine nachgelagerten Stufen. Nur der
Provider-Adapter ruft die Faktenprüfung auf, bevor er eine Antwort zurückgibt;
die Orchestrierung (``service.py``) verbindet die Schichten.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


APP = Path(__file__).resolve().parents[1] / "app"

FACT_CHECK = {"grounding", "grounding_claims", "grounding_constraints", "grounding_content", "grounding_references", "answer_plan", "answer_act_texts", "answer_sentences"}
DOMAIN_RULES = {"candidates", "candidate_context", "candidate_contract", "dialogue_flow", "result_time", "result_ordering"}
DATA_BASIS = {"kb_loader", "curation", "official_offer_source", "wfs_releases", "toilet_releases", "drinking_fountain_releases"}
LLM_ADAPTERS = {"providers"}
ORCHESTRATION = {"service", "main", "sessions", "llm_stages"}

FORBIDDEN = {
    "fact_check": (FACT_CHECK, LLM_ADAPTERS | ORCHESTRATION | DATA_BASIS | {"candidates", "candidate_context", "llm_selection", "config"}),
    "domain_rules": (DOMAIN_RULES, LLM_ADAPTERS | ORCHESTRATION | FACT_CHECK | {"formulation"}),
    "data_basis": (DATA_BASIS, LLM_ADAPTERS | ORCHESTRATION | FACT_CHECK | DOMAIN_RULES - {"result_ordering"} | {"formulation", "llm_selection"}),
}


def _internal_imports(module: str) -> set[str]:
    path = APP / f"{module}.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level >= 1 and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level >= 1:
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[1] for alias in node.names if alias.name.startswith("app."))
    return imported


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_does_not_depend_on_later_or_parallel_stages(layer: str) -> None:
    modules, forbidden = FORBIDDEN[layer]
    violations = {
        module: sorted(_internal_imports(module) & forbidden)
        for module in sorted(modules)
        if _internal_imports(module) & forbidden
    }
    assert violations == {}


def test_provider_adapter_cannot_return_an_unchecked_formulation() -> None:
    source = (APP / "providers" / "llm.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    method = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "formulate_answer"
    )
    calls = {
        node.func.id for node in ast.walk(method)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "validate_formulation" in calls
    returns = [node for node in ast.walk(method) if isinstance(node, ast.Return)]
    assert len(returns) == 1, "the only return must follow the validation"
