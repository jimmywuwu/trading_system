from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any

import yaml


class ValidationError(ValueError):
    """Raised when an artifact type or document shape is unsupported."""


ARTIFACT_TEMPLATES: dict[str, dict[str, Any]] = {
    "ResearchIdea": {
        "id": "",
        "created_at": "",
        "created_by": "",
        "summary": "",
        "suspected_mechanism": "",
        "candidate_sources": [],
        "candidate_symbols": [],
        "expected_horizon": "",
        "why_it_might_persist": "",
        "known_risks": [],
        "duplicate_of": "",
        "next_owner": "",
        "priority": "",
    },
    "MechanismNote": {
        "id": "",
        "research_idea_id": "",
        "mechanism_summary": "",
        "participants": {
            "forced_traders": "",
            "slow_traders": "",
            "liquidity_providers": "",
            "informed_traders": "",
        },
        "pressure_source": "",
        "expected_observable_footprints": [],
        "expected_decay_reason": "",
        "why_it_might_persist": "",
        "alternative_explanations": [],
        "invalidation_conditions": [],
    },
    "ResearchHypothesis": {
        "id": "",
        "mechanism_note_id": "",
        "statement": "",
        "trigger_condition": "",
        "target_symbol": "",
        "target_variable": "",
        "horizon": "",
        "expected_direction": "",
        "expected_effect_size": "",
        "null_hypothesis": "",
        "minimum_effect_after_cost": "",
        "assumptions": [],
        "failure_modes": [],
        "falsification_tests": [],
    },
    "ObservationRequirements": {
        "id": "",
        "hypothesis_id": "",
        "required_observations": [
            {
                "kind": "",
                "subject": "",
                "required_fields": [],
                "lookback_window": "",
                "observed_at_rule": "",
                "occurred_at_rule": "",
                "stale_tolerance": "",
                "required_for_signal": True,
            }
        ],
        "missing_data_policy": "",
        "late_arrival_policy": "",
        "replay_requirement": "",
        "data_quality_risks": [],
    },
    "DataProviderHandoff": {
        "id": "",
        "created_at": "",
        "created_by": "QUANT",
        "hypothesis_id": "",
        "source": "",
        "source_type": "",
        "required_fields": [],
        "subjects": [],
        "observation_kinds": [],
        "expected_latency": "",
        "timestamp_semantics": {"occurred_at_rule": "", "observed_at_rule": "", "timezone": "UTC"},
        "missing_data_policy_needed": "",
        "duplicate_policy_needed": "",
        "late_arrival_policy_needed": "",
        "revision_policy_needed": "",
        "replay_requirement": "",
        "minimum_fixture": "",
        "data_quality_risks": [],
        "quant_dependency": "",
        "requested_review": "",
    },
    "SignalContract": {
        "id": "",
        "signal_name": "",
        "hypothesis_id": "",
        "mechanism_summary": "",
        "required_kinds": [],
        "required_subjects": [],
        "required_payload_fields": [],
        "lookback_window": "",
        "stale_tolerance": "",
        "warmup_required": "",
        "direction_rule": "",
        "strength_rule": "",
        "confidence_rule": "",
        "reason_codes": [{"code": "", "meaning": ""}],
        "metadata_schema": {},
        "failure_modes": [],
        "minimum_tests": [],
        "trader_visible_semantics": "",
    },
    "SmokeReplayValidation": {
        "id": "",
        "signal_contract_id": "",
        "signal_name": "",
        "fixture": "",
        "tests_run": [],
        "passed": False,
        "failures": [],
        "timestamp_check": "",
        "lookahead_check": "",
        "determinism_check": "",
        "notes": "",
    },
    "SignalResearchResult": {
        "id": "",
        "hypothesis_id": "",
        "signal_contract_id": "",
        "data_scope": "",
        "signal_count": "",
        "horizons": [],
        "forward_return_summary": {},
        "strength_bucket_analysis": {},
        "confidence_bucket_analysis": {},
        "gross_edge": "",
        "cost_assumption": "",
        "net_edge_estimate": "",
        "preliminary_conclusion": "",
        "warnings": [],
    },
    "BenchmarkComparison": {
        "id": "",
        "research_result_id": "",
        "benchmarks": [
            {
                "name": "",
                "construction": "",
                "exposure": "",
                "total_return": "",
                "max_drawdown": "",
                "volatility": "",
                "sharpe": "",
                "turnover": "",
            }
        ],
        "strategy_vs_benchmark": "",
        "interpretation": "",
    },
    "RobustnessReview": {
        "id": "",
        "research_result_id": "",
        "parameter_grid": {},
        "train_test": {"split_rule": "", "train_result": "", "test_result": "", "continuous_state": True},
        "walk_forward": {"windows": [], "selected_params": [], "test_segments": [], "aggregate_result": ""},
        "parameter_stability": {"top_params": [], "neighborhood_stability": "", "overfit_warning": ""},
        "cost_sensitivity": "",
        "conclusion": "",
    },
    "RegimeAttribution": {
        "id": "",
        "research_result_id": "",
        "regime_definition": "",
        "regimes": [
            {
                "name": "",
                "bars": "",
                "signal_count": "",
                "strategy_return": "",
                "benchmark_return": "",
                "max_drawdown": "",
                "exposure": "",
                "trades": "",
                "fees": "",
                "notes": "",
            }
        ],
        "failure_regimes": [],
        "trader_risk_implications": "",
    },
    "ResearchReport": {
        "id": "",
        "hypothesis_id": "",
        "signal_contract_id": "",
        "summary": "",
        "data_scope": "",
        "methodology": "",
        "completed_checks": [],
        "partial_checks": [],
        "not_done_checks": [],
        "key_results": {},
        "benchmark_comparison": "",
        "robustness_summary": "",
        "regime_summary": "",
        "cost_sensitivity": "",
        "failure_modes": [],
        "conclusion_grade": "",
        "recommended_next_owner": "",
        "required_reviews": [],
    },
    "TraderHandoff": {
        "id": "",
        "created_at": "",
        "created_by": "QUANT",
        "hypothesis_id": "",
        "signal_contract_id": "",
        "signal_name": "",
        "reason_codes": [{"code": "", "meaning": ""}],
        "direction_semantics": "",
        "strength_interpretation": "",
        "confidence_interpretation": "",
        "expected_horizon": "",
        "expected_frequency": "",
        "expected_holding_period": "",
        "expected_turnover": "",
        "expected_exposure_profile": "",
        "cost_sensitivity_summary": "",
        "regime_behavior": "",
        "known_failure_modes": [],
        "data_integrity_status": "not_reviewed",
        "research_conclusion": "",
        "paper_trading_recommendation": "",
        "open_questions_for_trader": [],
    },
    "DecisionRecord": {
        "id": "",
        "created_at": "",
        "created_by": "HERMES",
        "decision": "",
        "status": "",
        "reason": "",
        "evidence": [],
        "owners": [],
        "follow_up_tasks": [],
        "do_not_repeat_until": "",
        "related_artifacts": [],
    },
}

REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    artifact_type: tuple(template.keys()) for artifact_type, template in ARTIFACT_TEMPLATES.items()
}

TRADER_HANDOFF_FORBIDDEN_FIELDS = ("quantity", "leverage", "order_size", "position_size", "max_position")


def list_artifact_types() -> list[str]:
    """Return supported artifact types in canonical workflow order."""

    return list(ARTIFACT_TEMPLATES)


def create_artifact_template(artifact_type: str) -> dict[str, Any]:
    """Return a deep-copied YAML-ready template for an artifact type."""

    if artifact_type not in ARTIFACT_TEMPLATES:
        supported = ", ".join(list_artifact_types())
        raise ValidationError(f"Unknown artifact type: {artifact_type}. Supported: {supported}")
    return {artifact_type: copy.deepcopy(ARTIFACT_TEMPLATES[artifact_type])}


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _validate_nested_required(prefix: str, value: Any, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}"
            if _is_blank(child):
                errors.append(f"{child_prefix} is required")
            else:
                _validate_nested_required(child_prefix, child, errors)
    elif isinstance(value, list):
        if not value:
            errors.append(f"{prefix} is required")
        for index, child in enumerate(value):
            _validate_nested_required(f"{prefix}[{index}]", child, errors)


def validate_artifact(document: dict[str, Any]) -> list[str]:
    """Validate one artifact document and return human-readable errors.

    The validator intentionally stays schema-light: it enforces the workflow gates
    that matter most for early automation while keeping artifacts editable by hand.
    """

    errors: list[str] = []
    if not isinstance(document, dict) or len(document) != 1:
        return ["artifact document must contain exactly one top-level artifact type"]

    artifact_type, artifact = next(iter(document.items()))
    if artifact_type not in ARTIFACT_TEMPLATES:
        return [f"Unknown artifact type: {artifact_type}"]
    if not isinstance(artifact, dict):
        return [f"{artifact_type} must be a mapping"]

    for field in REQUIRED_FIELDS[artifact_type]:
        if field not in artifact or _is_blank(artifact[field]):
            errors.append(f"{artifact_type}.{field} is required")
        else:
            _validate_nested_required(f"{artifact_type}.{field}", artifact[field], errors)

    if artifact_type == "TraderHandoff":
        for field in TRADER_HANDOFF_FORBIDDEN_FIELDS:
            if field in artifact:
                errors.append(f"TraderHandoff must not define {field}")

    if artifact_type == "SignalContract":
        for rule_field in ("direction_rule", "strength_rule", "confidence_rule"):
            if _is_blank(artifact.get(rule_field)):
                errors.append(f"SignalContract.{rule_field} is required before implementation")

    return sorted(set(errors))


def load_artifact(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text())
    if loaded is None:
        raise ValidationError(f"{path} is empty")
    if not isinstance(loaded, dict):
        raise ValidationError(f"{path} must contain a YAML mapping")
    return loaded


def write_artifact(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _cmd_list(_: argparse.Namespace) -> int:
    for artifact_type in list_artifact_types():
        print(artifact_type)
    return 0


def _cmd_new(args: argparse.Namespace) -> int:
    document = create_artifact_template(args.artifact_type)
    if args.output:
        write_artifact(Path(args.output), document)
    else:
        print(yaml.safe_dump(document, sort_keys=False), end="")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        document = load_artifact(Path(args.path))
    except ValidationError as exc:
        print(str(exc))
        return 2
    errors = validate_artifact(document)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"{args.path}: valid")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and validate Quant workflow artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List supported artifact types.")
    list_parser.set_defaults(func=_cmd_list)

    new_parser = subparsers.add_parser("new", help="Create an artifact template.")
    new_parser.add_argument("artifact_type", choices=list_artifact_types())
    new_parser.add_argument("--output", "-o", help="Write template to this YAML file instead of stdout.")
    new_parser.set_defaults(func=_cmd_new)

    validate_parser = subparsers.add_parser("validate", help="Validate an artifact YAML file.")
    validate_parser.add_argument("path")
    validate_parser.set_defaults(func=_cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
