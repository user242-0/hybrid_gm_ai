# Action Proposal DSL v0.1

## Overview

Action Proposal DSL is a declarative format for proposing new actions to the game engine.
Proposals go through a multi-stage validation pipeline before being accepted.

## Purpose

- Allow external agents (RO, LLM, pack authors) to propose actions at runtime
- Provide a structured validation gate that catches invalid or dangerous proposals
- Enable a gradual adoption path: shadow mode first, promotion later

## Proposal YAML Format

```yaml
proposal:
  id: "search_dumpster"
  label: "ゴミ箱を漁る"
  time_min: 8
  target: null
  requirements:
    has_location: "事件現場_路地裏"
  effects:
    evidence_score: "+3"
  source: "RO"
  rationale: "現場に未回収の証拠がある可能性"
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique action identifier (ASCII, snake_case) |
| `label` | string | Display label for HUD |
| `time_min` | int | Time cost in minutes (>= 0) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `target` | string or null | Target entity |
| `requirements` | dict | Pre-conditions (same format as action_definitions) |
| `effects` | dict | World state changes |
| `source` | string | Who proposed this ("RO", "LLM", "pack") |
| `rationale` | string | Human-readable reason for proposal |

## Validation Checks

| ID | Name         | Description                                                                   | v0.1        |
| -- | ------------ | ----------------------------------------------------------------------------- | ----------- |
| A  | Syntax       | Required fields present, types correct                                        | Implemented |
| B  | Uniqueness   | No duplicate `id` in active actions                                           | Implemented |
| C  | Requirements | `requirements` keys are valid                                                 | Implemented |
| D  | Effects      | `effects` structure and target paths are valid                                | Implemented |
| E  | Safety       | Effects do not violate safety limits                                          | Implemented |
| F  | Narrative    | Tags, source, mode, tone, and rationale are consistent with narrative context | Implemented |

### Validator Contract

`validate_proposal()` returns a `ValidationReport`.

The report contract is stable in v0.1:

```python
{
    "overall": "PASS" | "UNKNOWN" | "REJECT",
    "checks": {
        "A_syntax": "PASS" | "UNKNOWN" | "REJECT",
        "B_uniqueness": "PASS" | "UNKNOWN" | "REJECT",
        "C_requirements": "PASS" | "UNKNOWN" | "REJECT",
        "D_effects": "PASS" | "UNKNOWN" | "REJECT",
        "E_safety": "PASS" | "UNKNOWN" | "REJECT",
        "F_narrative": "PASS" | "UNKNOWN" | "REJECT",
    },
    "reasons": {
        "...": "human-readable reason"
    },
    "reason_codes": {
        "...": "stable_machine_readable_reason_code"
    }
}
```

Check order is fixed:

```python
CHECK_ORDER = (
    "A_syntax",
    "B_uniqueness",
    "C_requirements",
    "D_effects",
    "E_safety",
    "F_narrative",
)
```

`overall` is determined as follows:

* If any check is `REJECT`, overall is `REJECT`.
* If all checks are `PASS`, overall is `PASS`.
* Otherwise, overall is `UNKNOWN`.

Human-readable `reasons` may change over time. Callers should depend on `reason_codes`, check IDs, and result values instead.

### Check B: Uniqueness

`validate_proposal()` accepts optional `active_action_ids`.

* If `active_action_ids` is not provided, B returns `UNKNOWN`.
* If the proposal `id` already exists in `active_action_ids`, B returns `REJECT`.
* If the proposal `id` is new, B returns `PASS`.

### Check C: Requirements

`validate_proposal()` accepts optional `known_requirement_keys`.

* If `requirements` is missing, `None`, or `{}`, C returns `PASS`.
* If `requirements` is not a dict, C returns `REJECT`.
* If `requirements` is a dict but `known_requirement_keys` is not provided, C returns `UNKNOWN`.
* If `requirements` contains unknown keys, C returns `REJECT`.
* If all requirement keys are known, C returns `PASS`.

v0.1 only validates requirement key names. It does not validate requirement values or connect to `RequirementsChecker` yet.

### Check D: Effects

`validate_proposal()` accepts optional `known_effect_paths`.

* If `effects` is missing, `None`, `{}`, or `[]`, D returns `PASS`.
* Dict-style effects use keys as effect paths.
* List-style effects require each item to be a dict with `op` and `path`.
* Supported list-style ops in v0.1 are `add` and `set`.
* If `known_effect_paths` is not provided for non-empty effects, D returns `UNKNOWN`.
* If an effect path is unknown, D returns `REJECT`.

v0.1 validates effects structure and target paths only. It does not apply effects to world state.

### Check E: Safety

`validate_proposal()` accepts optional `safety_limits`.

* If `effects` is missing, `None`, `{}`, or `[]`, E returns `PASS`.
* If non-empty effects exist but `safety_limits` is not provided, E returns `UNKNOWN`.
* `forbidden_effect_paths` rejects attempts to modify prohibited paths.
* `max_abs_delta` rejects excessive numeric `add` deltas.
* `max_abs_delta_by_path` overrides the global delta limit for specific paths.
* `set` effects are not checked by delta limit in v0.1.
* If an `add` value cannot be interpreted numerically, E returns `UNKNOWN`.

v0.1 does not inspect or mutate live world state.

### Check F: Narrative

`validate_proposal()` accepts optional `narrative_context`.

* If `narrative_context` is not provided or is not a dict, F returns `UNKNOWN`.
* `allowed_sources` can reject proposal sources outside the allowed set.
* `require_rationale` can require a non-empty `rationale`.
* `modes` can constrain which current narrative mode the proposal is valid for.
* `allowed_modes` can reject unknown or unsupported proposal modes.
* `tone_tags` can be checked against the current tone set.
* `tags` can be checked against `forbidden_tags`.

v0.1 only checks mechanical tag/context consistency. It does not judge whether an action is interesting, dramatic, or good storytelling, and it does not call an LLM.

## Runtime-facing v0.1 Adapters

Action Proposal DSL v0.1 now has a staged runtime-facing pipeline.

```text
proposal
→ validator A-F
→ shadow record
→ shadow log
→ advisory item
→ advisory feed
→ read-only provider
→ HUD read-only display
```

### Shadow Adapter

Shadow mode validates proposals but does not execute them.

* `validate_proposal_shadow(proposal, context=None) -> dict`
* `append_shadow_log(path, record) -> None`
* `build_shadow_record(...) -> dict`
* `validate_and_build_shadow_record(...) -> dict`

Standard shadow log filename:

```text
action_proposal_shadow.jsonl
```

Default location:

```text
jobs/%Y%m%d_quick/action_proposal_shadow.jsonl
```

Shadow record schema:

```text
action_proposal_shadow.v0.1
```

Shadow records are audit logs. They should not be treated as temporary scratch files in the same way as generated scene graph debug artifacts.

### Advisory Adapter

Advisory mode converts accepted shadow records into display candidates.

* `build_advisory_item(shadow_record) -> dict | None`
* `build_advisory_items(shadow_records) -> list[dict]`
* `validate_proposal_to_advisory(...) -> dict | None`

Only shadow records with `accepted is True` and `overall == "PASS"` become advisory items.

Advisory item schema:

```text
action_proposal_advisory.v0.1
```

### Advisory Feed

The advisory feed converts advisory items into stable HUD-facing display items.

* `build_display_item(advisory_item) -> dict | None`
* `build_advisory_feed(advisory_items, limit=5, run_id=None) -> dict`
* `build_advisory_feed_from_shadow_records(...) -> dict`
* `load_jsonl_records(path) -> list[dict]`
* `build_advisory_feed_from_shadow_log(...) -> dict`

Feed schema:

```text
action_proposal_advisory_feed.v0.1
```

Display item schema:

```text
action_proposal_advisory_display_item.v0.1
```

### Read-only Advisory Provider

The provider is the safe read-only entry point for HUD.

* `get_advisory_feed(...) -> dict`
* `get_advisory_display_items(...) -> list[dict]`
* `has_advisory_items(...) -> bool`

Provider schema:

```text
action_proposal_advisory_provider.v0.1
```

The provider reads shadow logs and returns display items. It does not write logs, mutate game state, register actions, or call ActionPipeline.

### HUD Read-only Display

Director HUD can display advisory items in an `AI提案` section.

Current constraints:

* Display only
* Not clickable
* Not executable
* Not mixed into the Actions listbox
* No ActionPipeline connection
* No action_registry connection
* No world state mutation

This is still Advisory display, not Provisional action adoption.
