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


@dataclass
class ValidationReport:
    """Aggregated validation result for a proposal."""

    checks: dict[str, ValidationResult] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)

    @property
    def overall(self) -> ValidationResult:
        if any(v == ValidationResult.REJECT for v in self.checks.values()):
            return ValidationResult.REJECT
        if all(v == ValidationResult.PASS for v in self.checks.values()):
            return ValidationResult.PASS
        return ValidationResult.UNKNOWN


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


def validate_proposal(
    proposal: dict[str, Any],
    active_action_ids: set[str] | list[str] | tuple[str, ...] | None = None,
    known_requirement_keys: set[str] | list[str] | tuple[str, ...] | None = None,
    known_effect_paths: set[str] | list[str] | tuple[str, ...] | None = None,
) -> ValidationReport:
    """Run all validation checks (A-D implemented, E-F stubs)."""
    report = ValidationReport()

    # A: Syntax
    result_a, reason_a = validate_syntax(proposal)
    report.checks["A_syntax"] = result_a
    if reason_a:
        report.reasons["A_syntax"] = reason_a

    # B: Uniqueness
    if active_action_ids is None:
        report.checks["B_uniqueness"] = ValidationResult.UNKNOWN
        report.reasons["B_uniqueness"] = "active_action_ids not provided"
    else:
        proposal_id = proposal.get("id") if isinstance(proposal, dict) else None
        if proposal_id in active_action_ids:
            report.checks["B_uniqueness"] = ValidationResult.REJECT
            report.reasons["B_uniqueness"] = f"duplicate action id: {proposal_id!r}"
        else:
            report.checks["B_uniqueness"] = ValidationResult.PASS

    # C: Requirements
    result_c, reason_c = validate_requirements(proposal, known_requirement_keys)
    report.checks["C_requirements"] = result_c
    if reason_c:
        report.reasons["C_requirements"] = reason_c

    # D: Effects
    result_d, reason_d = validate_effects(proposal, known_effect_paths)
    report.checks["D_effects"] = result_d
    if reason_d:
        report.reasons["D_effects"] = reason_d

    # E-F: stubs
    for check_id in ("E_safety", "F_narrative"):
        report.checks[check_id] = ValidationResult.UNKNOWN
        report.reasons[check_id] = "not yet implemented"

    return report
