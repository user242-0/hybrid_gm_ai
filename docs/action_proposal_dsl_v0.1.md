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

| ID | Name | Description | v0.1 |
|----|------|-------------|------|
| A | Syntax | Required fields present, types correct | Implemented |
| B | Uniqueness | No duplicate `id` in active actions | UNKNOWN stub |
| C | Requirements | requirements keys are valid | UNKNOWN stub |
| D | Effects | effects targets exist in world state | UNKNOWN stub |
| E | Safety | No harmful side effects (harm threshold) | UNKNOWN stub |
| F | Narrative | Consistent with current mode/tone | UNKNOWN stub |

## Result Values

Each check returns one of three values:

- **PASS** - Check succeeded
- **REJECT** - Check failed with a reason
- **UNKNOWN** - Check not yet implemented or inconclusive

## Adoption Stages

1. **Shadow** - Proposals are validated but not executed. Results logged only.
2. **Advisory** - Validated proposals shown to player as suggestions.
3. **Provisional** - Proposals auto-added to action list but marked as provisional.
4. **Promotion** - Proven proposals become permanent pack actions.

## Design Principles

1. Proposals are data, not code
2. Validation is deterministic and reproducible
3. Each check is independent and can be run in any order
4. UNKNOWN is a valid result (not a failure)
5. Shadow mode must be safe (no world state mutation)
6. Proposals carry their rationale for auditability
7. The DSL is versioned; breaking changes bump the version
