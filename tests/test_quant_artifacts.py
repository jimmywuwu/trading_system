from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from quant_tools.artifacts import (
    ValidationError,
    create_artifact_template,
    list_artifact_types,
    validate_artifact,
)


def test_signal_contract_template_contains_required_research_gate_fields() -> None:
    template = create_artifact_template("SignalContract")

    assert set(template) == {"SignalContract"}
    signal_contract = template["SignalContract"]
    assert signal_contract["signal_name"] == ""
    assert signal_contract["hypothesis_id"] == ""
    assert signal_contract["direction_rule"] == ""
    assert signal_contract["strength_rule"] == ""
    assert signal_contract["confidence_rule"] == ""
    assert signal_contract["reason_codes"] == [{"code": "", "meaning": ""}]
    assert "failure_modes" in signal_contract
    assert "trader_visible_semantics" in signal_contract


def test_validate_artifact_reports_missing_required_fields() -> None:
    invalid = {"ResearchHypothesis": {"id": "hyp_001", "statement": "funding high means short"}}

    errors = validate_artifact(invalid)

    assert "ResearchHypothesis.horizon is required" in errors
    assert "ResearchHypothesis.null_hypothesis is required" in errors
    assert "ResearchHypothesis.falsification_tests is required" in errors


def test_validate_trader_handoff_rejects_quant_sizing_leakage() -> None:
    handoff = create_artifact_template("TraderHandoff")
    trader_handoff = handoff["TraderHandoff"]
    for key in trader_handoff:
        if isinstance(trader_handoff[key], str):
            trader_handoff[key] = f"filled_{key}"
    trader_handoff["reason_codes"] = [{"code": "leverage_pressure_short", "meaning": "short pressure"}]
    trader_handoff["known_failure_modes"] = ["spot-led bull market"]
    trader_handoff["open_questions_for_trader"] = ["Should this be traded at all?"]
    trader_handoff["quantity"] = 1.0
    trader_handoff["leverage"] = 3

    errors = validate_artifact(handoff)

    assert "TraderHandoff must not define quantity" in errors
    assert "TraderHandoff must not define leverage" in errors


def test_unknown_artifact_type_is_rejected() -> None:
    try:
        create_artifact_template("PrettyEquityCurve")
    except ValidationError as exc:
        assert "Unknown artifact type" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("unknown artifact type should fail")


def test_cli_new_and_validate_round_trip(tmp_path: Path) -> None:
    artifact_path = tmp_path / "signal_contract.yaml"

    subprocess.run(
        [sys.executable, "-m", "quant_tools.artifacts", "new", "SignalContract", "--output", str(artifact_path)],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )

    loaded = yaml.safe_load(artifact_path.read_text())
    assert list(loaded) == ["SignalContract"]
    assert "SignalContract" in list_artifact_types()

    result = subprocess.run(
        [sys.executable, "-m", "quant_tools.artifacts", "validate", str(artifact_path)],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "SignalContract.signal_name is required" in result.stdout
