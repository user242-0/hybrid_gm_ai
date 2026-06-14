"""Action Proposal validator — syntax check + stub checks B-F."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationResult(Enum):
    PASS = "PASS"
    REJECT = "REJECT"
    UNKNOWN = "UNKNOWN"


CHECK_ORDER = (
    "A_syntax",
    "B_uniqueness",
    "C_requirements",
    "D_effects",
    "E_safety",
    "F_narrative",
)


_REASON_CODE_BY_REASON = {
    "proposal must be a dict": "missing_required_fields",
    "label must be a non-empty string": "missing_required_fields",
    "requirements must be a dict": "unknown_requirement_keys",
    "known_requirement_keys not provided": "known_requirement_keys_not_provided",
    "known_effect_paths not provided": "known_effect_paths_not_provided",
    "effects must be a dict or list": "unknown_effect_paths",
    "effect item must be a dict": "unknown_effect_paths",
    "effect item missing op": "unknown_effect_paths",
    "effect item missing path": "unknown_effect_paths",
    "effect path must be a non-empty string": "unknown_effect_paths",
    "safety_limits not provided": "safety_limits_not_provided",
    "safety_limits must be a dict": "safety_limits_not_provided",
    "effect item must be a dict for safety check": "unknown_effect_paths",
    "effect path unavailable for safety check": "unknown_effect_paths",
    "effects unavailable for safety check": "unknown_effect_paths",
    "narrative_context not provided": "narrative_context_not_provided",
    "narrative_context must be a dict": "narrative_context_not_provided",
    "proposal unavailable for narrative check": "narrative_context_not_provided",
    "rationale required": "missing_rationale",
    "modes must be a list, tuple, or set": "mode_not_allowed",
    "tone_tags must be a list, tuple, or set": "tone_mismatch",
    "tone_tags do not overlap narrative tone": "tone_mismatch",
    "tags must be a list, tuple, or set": "forbidden_tag",
}


def _reason_code_for_reason(reason: str) -> str:
    if reason in _REASON_CODE_BY_REASON:
        return _REASON_CODE_BY_REASON[reason]
    if reason.startswith("missing required fields:"):
        return "missing_required_fields"
    if reason.startswith("id must be ASCII snake_case"):
        return "invalid_id"
    if reason.startswith("time_min must be a non-negative int"):
        return "missing_required_fields"
    if reason.startswith("duplicate action id:"):
        return "duplicate_action_id"
    if reason.startswith("unknown requirement keys:"):
        return "unknown_requirement_keys"
    if reason.startswith("unknown effect paths:"):
        return "unknown_effect_paths"
    if reason.startswith("unknown effect op:"):
        return "unknown_effect_paths"
    if reason.startswith("forbidden effect path"):
        return "forbidden_effect_path"
    if reason.startswith("forbidden effect paths"):
        return "forbidden_effect_path"
    if "exceeds max_abs_delta" in reason:
        return "delta_exceeds_limit"
    if "not numeric" in reason:
        return "delta_exceeds_limit"
    if "unavailable for safety check" in reason:
        return "delta_exceeds_limit"
    if reason.startswith("source not allowed:"):
        return "invalid_source"
    if reason.startswith("current_mode not in proposal modes:"):
        return "mode_not_allowed"
    if reason.startswith("modes outside allowed_modes:"):
        return "mode_not_allowed"
    if reason.startswith("forbidden tags present:"):
        return "forbidden_tag"
    return "validation_failed"


@dataclass
class ValidationReport:
    """Aggregated validation result for a proposal."""

    checks: dict[str, ValidationResult] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)
    reason_codes: dict[str, str] = field(default_factory=dict)

    @property
    def overall(self) -> ValidationResult:
        if any(v == ValidationResult.REJECT for v in self.checks.values()):
            return ValidationResult.REJECT
        if self.checks and all(v == ValidationResult.PASS for v in self.checks.values()):
            return ValidationResult.PASS
        return ValidationResult.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/log friendly representation of the report."""
        return {
            "overall": self.overall.value,
            "checks": {check_id: result.value for check_id, result in self.checks.items()},
            "reasons": dict(self.reasons),
            "reason_codes": dict(self.reason_codes),
        }


def _record_check(
    report: ValidationReport,
    check_id: str,
    result: ValidationResult,
    reason: str = "",
    reason_code: str | None = None,
) -> None:
    report.checks[check_id] = result
    if reason:
        report.reasons[check_id] = reason
        report.reason_codes[check_id] = reason_code or _reason_code_for_reason(reason)


_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

REQUIRED_FIELDS = {"id", "label", "time_min"}


def validate_syntax(proposal: dict[str, Any]) -> tuple[ValidationResult, str]:
    """Check A: required fields present, types correct."""
    if not isinstance(proposal, dict):
        return ValidationResult.REJECT, "proposal must be a dict"

    missing = REQUIRED_FIELDS - set(proposal.keys())
    if missing:
        return ValidationResult.REJECT, f"missing required fields: {sorted(missing)}"

    pid = proposal["id"]
    if not isinstance(pid, str) or not _ID_PATTERN.match(pid):
        return ValidationResult.REJECT, f"id must be ASCII snake_case, got {pid!r}"

    label = proposal["label"]
    if not isinstance(label, str) or not label.strip():
        return ValidationResult.REJECT, "label must be a non-empty string"

    time_min = proposal["time_min"]
    if not isinstance(time_min, int) or time_min < 0:
        return ValidationResult.REJECT, f"time_min must be a non-negative int, got {time_min!r}"

    return ValidationResult.PASS, ""


def validate_requirements(
    proposal: dict[str, Any],
    known_requirement_keys: set[str] | list[str] | tuple[str, ...] | None = None,
) -> tuple[ValidationResult, str]:
    """Check C: requirement keys are known when requirements are provided."""
    requirements = proposal.get("requirements") if isinstance(proposal, dict) else None
    if requirements is None or requirements == {}:
        return ValidationResult.PASS, ""

    if not isinstance(requirements, dict):
        return ValidationResult.REJECT, "requirements must be a dict"

    if known_requirement_keys is None:
        return ValidationResult.UNKNOWN, "known_requirement_keys not provided"

    known_keys = set(known_requirement_keys)
    unknown_keys = sorted(set(requirements.keys()) - known_keys)
    if unknown_keys:
        return ValidationResult.REJECT, f"unknown requirement keys: {unknown_keys}"

    return ValidationResult.PASS, ""


def validate_effects(
    proposal: dict[str, Any],
    known_effect_paths: set[str] | list[str] | tuple[str, ...] | None = None,
) -> tuple[ValidationResult, str]:
    """Check D: effect shape and known target paths."""
    effects = proposal.get("effects") if isinstance(proposal, dict) else None
    if effects is None or effects == {} or effects == []:
        return ValidationResult.PASS, ""

    if isinstance(effects, dict):
        if known_effect_paths is None:
            return ValidationResult.UNKNOWN, "known_effect_paths not provided"

        known_paths = set(known_effect_paths)
        unknown_paths = sorted(set(effects.keys()) - known_paths)
        if unknown_paths:
            return ValidationResult.REJECT, f"unknown effect paths: {unknown_paths}"

        return ValidationResult.PASS, ""

    if isinstance(effects, list):
        effect_paths: list[str] = []
        for item in effects:
            if not isinstance(item, dict):
                return ValidationResult.REJECT, "effect item must be a dict"
            if "op" not in item:
                return ValidationResult.REJECT, "effect item missing op"
            if "path" not in item:
                return ValidationResult.REJECT, "effect item missing path"
            if item["op"] not in {"add", "set"}:
                return ValidationResult.REJECT, f"unknown effect op: {item['op']!r}"

            path = item["path"]
            if not isinstance(path, str) or not path:
                return ValidationResult.REJECT, "effect path must be a non-empty string"
            effect_paths.append(path)

        if known_effect_paths is None:
            return ValidationResult.UNKNOWN, "known_effect_paths not provided"

        known_paths = set(known_effect_paths)
        unknown_paths = sorted(set(effect_paths) - known_paths)
        if unknown_paths:
            return ValidationResult.REJECT, f"unknown effect paths: {unknown_paths}"

        return ValidationResult.PASS, ""

    return ValidationResult.REJECT, "effects must be a dict or list"


def _parse_add_delta(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _delta_limit_for_path(path: str, safety_limits: dict[str, Any]) -> Any:
    limits_by_path = safety_limits.get("max_abs_delta_by_path")
    if isinstance(limits_by_path, dict) and path in limits_by_path:
        return limits_by_path[path]
    return safety_limits.get("max_abs_delta")


def _check_add_delta(path: str, value: Any, safety_limits: dict[str, Any]) -> tuple[ValidationResult, str]:
    limit = _delta_limit_for_path(path, safety_limits)
    if limit is None:
        return ValidationResult.PASS, ""

    delta = _parse_add_delta(value)
    if delta is None:
        return ValidationResult.UNKNOWN, f"add value for {path!r} is not numeric"

    limit_value = _parse_add_delta(limit)
    if limit_value is None:
        return ValidationResult.UNKNOWN, f"delta limit for {path!r} is not numeric"

    if abs(delta) > limit_value:
        return ValidationResult.REJECT, f"add delta for {path!r} exceeds max_abs_delta {limit_value:g}: {value!r}"

    return ValidationResult.PASS, ""


def validate_safety(
    proposal: dict[str, Any],
    safety_limits: dict[str, Any] | None = None,
) -> tuple[ValidationResult, str]:
    """Check E: coarse effect-only safety limits."""
    effects = proposal.get("effects") if isinstance(proposal, dict) else None
    if effects is None or effects == {} or effects == []:
        return ValidationResult.PASS, ""

    if safety_limits is None:
        return ValidationResult.UNKNOWN, "safety_limits not provided"
    if not isinstance(safety_limits, dict):
        return ValidationResult.UNKNOWN, "safety_limits must be a dict"

    forbidden_paths = set(safety_limits.get("forbidden_effect_paths") or ())

    if isinstance(effects, dict):
        changed_paths = set(effects.keys())
        forbidden_changed_paths = sorted(changed_paths & forbidden_paths)
        if forbidden_changed_paths:
            return ValidationResult.REJECT, f"forbidden effect paths changed: {forbidden_changed_paths}"

        for path, value in effects.items():
            result, reason = _check_add_delta(path, value, safety_limits)
            if result != ValidationResult.PASS:
                return result, reason

        return ValidationResult.PASS, ""

    if isinstance(effects, list):
        for item in effects:
            if not isinstance(item, dict):
                return ValidationResult.UNKNOWN, "effect item must be a dict for safety check"

            path = item.get("path")
            if not isinstance(path, str) or not path:
                return ValidationResult.UNKNOWN, "effect path unavailable for safety check"

            if path in forbidden_paths:
                return ValidationResult.REJECT, f"forbidden effect path changed: {path!r}"

            if item.get("op") == "add":
                if "value" not in item:
                    return ValidationResult.UNKNOWN, f"add value for {path!r} unavailable for safety check"
                result, reason = _check_add_delta(path, item["value"], safety_limits)
                if result != ValidationResult.PASS:
                    return result, reason

        return ValidationResult.PASS, ""

    return ValidationResult.UNKNOWN, "effects unavailable for safety check"


def _as_set(value: Any) -> set[Any]:
    return set(value or ())


def validate_narrative(
    proposal: dict[str, Any],
    narrative_context: dict[str, Any] | None = None,
) -> tuple[ValidationResult, str]:
    """Check F: mechanical tag/context consistency only."""
    if narrative_context is None:
        return ValidationResult.UNKNOWN, "narrative_context not provided"
    if not isinstance(narrative_context, dict):
        return ValidationResult.UNKNOWN, "narrative_context must be a dict"
    if not isinstance(proposal, dict):
        return ValidationResult.UNKNOWN, "proposal unavailable for narrative check"

    source = proposal.get("source")
    if "allowed_sources" in narrative_context and source is not None:
        allowed_sources = _as_set(narrative_context.get("allowed_sources"))
        if source not in allowed_sources:
            return ValidationResult.REJECT, f"source not allowed: {source!r}"

    if narrative_context.get("require_rationale") is True:
        rationale = proposal.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            return ValidationResult.REJECT, "rationale required"

    modes = proposal.get("modes")
    if modes is not None:
        if not isinstance(modes, list | tuple | set):
            return ValidationResult.REJECT, "modes must be a list, tuple, or set"

        mode_set = set(modes)
        current_mode = narrative_context.get("current_mode")
        if current_mode not in mode_set:
            return ValidationResult.REJECT, f"current_mode not in proposal modes: {current_mode!r}"

        if "allowed_modes" in narrative_context:
            allowed_modes = _as_set(narrative_context.get("allowed_modes"))
            disallowed_modes = sorted(mode_set - allowed_modes)
            if disallowed_modes:
                return ValidationResult.REJECT, f"modes outside allowed_modes: {disallowed_modes}"

    tone_tags = proposal.get("tone_tags")
    if tone_tags is not None:
        if not isinstance(tone_tags, list | tuple | set):
            return ValidationResult.REJECT, "tone_tags must be a list, tuple, or set"

        if "tone" in narrative_context:
            tone = _as_set(narrative_context.get("tone"))
            if tone and not (set(tone_tags) & tone):
                return ValidationResult.UNKNOWN, "tone_tags do not overlap narrative tone"

    tags = proposal.get("tags")
    if tags is not None:
        if not isinstance(tags, list | tuple | set):
            return ValidationResult.REJECT, "tags must be a list, tuple, or set"

        forbidden_tags = _as_set(narrative_context.get("forbidden_tags"))
        blocked_tags = sorted(set(tags) & forbidden_tags)
        if blocked_tags:
            return ValidationResult.REJECT, f"forbidden tags present: {blocked_tags}"

    return ValidationResult.PASS, ""


def validate_proposal(
    proposal: dict[str, Any],
    active_action_ids: set[str] | list[str] | tuple[str, ...] | None = None,
    known_requirement_keys: set[str] | list[str] | tuple[str, ...] | None = None,
    known_effect_paths: set[str] | list[str] | tuple[str, ...] | None = None,
    safety_limits: dict[str, Any] | None = None,
    narrative_context: dict[str, Any] | None = None,
) -> ValidationReport:
    """Run all validation checks."""
    report = ValidationReport()

    # A: Syntax
    result_a, reason_a = validate_syntax(proposal)
    _record_check(report, "A_syntax", result_a, reason_a)

    # B: Uniqueness
    if active_action_ids is None:
        _record_check(
            report,
            "B_uniqueness",
            ValidationResult.UNKNOWN,
            "active_action_ids not provided",
            "active_action_ids_not_provided",
        )
    else:
        proposal_id = proposal.get("id") if isinstance(proposal, dict) else None
        if proposal_id in active_action_ids:
            _record_check(
                report,
                "B_uniqueness",
                ValidationResult.REJECT,
                f"duplicate action id: {proposal_id!r}",
                "duplicate_action_id",
            )
        else:
            _record_check(report, "B_uniqueness", ValidationResult.PASS)

    # C: Requirements
    result_c, reason_c = validate_requirements(proposal, known_requirement_keys)
    _record_check(report, "C_requirements", result_c, reason_c)

    # D: Effects
    result_d, reason_d = validate_effects(proposal, known_effect_paths)
    _record_check(report, "D_effects", result_d, reason_d)

    # E: Safety
    result_e, reason_e = validate_safety(proposal, safety_limits)
    _record_check(report, "E_safety", result_e, reason_e)

    # F: Narrative
    result_f, reason_f = validate_narrative(proposal, narrative_context)
    _record_check(report, "F_narrative", result_f, reason_f)

    return report
