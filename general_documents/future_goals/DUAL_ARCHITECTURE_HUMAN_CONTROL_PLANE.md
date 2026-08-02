# Dual Architecture + Human Control Plane

## Status

- Document status: Concept / Architecture Direction v0.1
- Intended sharing point: GM-AI Session 60-0
- Implementation status: Not yet implemented
- Primary purpose: Preserve human understanding, supervision, and control as GM-AI grows beyond what one person can continuously hold in working memory

---

## 1. Executive Summary

GM-AI is based on a Dual Architecture:

1. **Blueprint Intelligence**
2. **Deterministic Machine Core**

Blueprint Intelligence interprets situations, forms intent, and generates proposals.  
Deterministic Machine Core validates actions, advances Operations, mutates authoritative state, and guarantees deterministic constraints.

As Operation-related responsibilities and data flows become more complex, the existing HUD/UI no longer exposes enough information for a human developer to understand what the system is doing. Following the player-facing HUD alone does not reveal the causal chain across Action, Operation, Transition, Memory, Belief, and ContextBundle.

To solve this, GM-AI introduces a cross-cutting human-facing control plane:

> **Control & Legibility Layer**

This layer does not become a third game-logic engine. It does not own intelligence or authoritative state transitions. Instead, it projects the behavior of the Dual Architecture into a form that a human can inspect, understand, verify, and safely control.

The resulting architecture is:

> **Dual Architecture + Human Control Plane**

The core design goal is:

> GM-AI may become more capable than its creator can understand from source code alone, but it must not become impossible for its creator to supervise, explain, and control.

---

## 2. Background

The GM-AI data system has become increasingly complex, especially around Operation processing.

The current cognitive-behavioral flow includes concepts such as:

```text
HUD Action
→ Action validation / execution
→ Operation start or progression
→ Operation Transition
→ RC Memory projection
→ Belief update
→ ContextBundle reconstruction
→ next RC_AI advisory
```

However, the existing HUD/UI remains close to its earlier form. It displays player-facing state and selected intelligence outputs, but it does not expose the full causal structure of Operation progression.

This creates a growing gap:

```text
Internal system complexity
        >
Human-visible system explanation
```

The problem is not simply that the code is large. The deeper problem is that the human operator cannot reliably answer questions such as:

- Which Action caused this Operation Transition?
- Why did this Operation advance?
- Which Transition produced this Memory?
- Which Memory changed this Belief?
- Where did this ContextBundle value come from?
- What changed before and after the latest action?
- Why is this Operation blocked?
- Can the same execution be reproduced?
- Can a human intervention be recorded and safely reversed?

The Control & Legibility Layer exists to close this gap.

---

## 3. Architecture Overview

```text
                         Human
                    inspect / control
                           ↑↓
              Control & Legibility Layer
                 /                       \
                /                         \
     Blueprint Intelligence       Deterministic Machine Core
     interpretation / proposal     validation / execution / state
```

This should not be interpreted as a Triple Architecture with three equal game engines.

The system remains a Dual Architecture internally:

```text
Blueprint Intelligence
        ×
Deterministic Machine Core
```

The Control & Legibility Layer is a **Human Control Plane** placed across both sides.

It observes, explains, traces, and submits controlled commands, but does not become an independent source of game truth.

---

## 4. Responsibility of Each Area

### 4.1 Blueprint Intelligence

Blueprint Intelligence is responsible for interpretation and proposal.

Examples:

- Interpreting ContextBundle
- Forming Intent
- Generating RC_AI advisory
- Assigning meaning to Memory and Belief
- Producing future LLM-assisted reasoning
- Suggesting possible actions under multiple valid interpretations

Its central question is:

> What does this situation mean, and what could be done next?

---

### 4.2 Deterministic Machine Core

Deterministic Machine Core is responsible for validation, execution, and authoritative state mutation.

Examples:

- Action validation
- Action execution
- Operation start, progression, completion, or failure
- MiniGoal progression
- World state mutation
- Operation Transition emission
- Idempotency guarantees
- Actor isolation
- Save/load consistency
- Prohibited-action enforcement
- Deterministic rule execution

Its central question is:

> What is allowed to happen, and what state change is officially committed?

---

### 4.3 Control & Legibility Layer

Control & Legibility Layer is responsible for human comprehension, inspection, supervision, and controlled intervention.

Examples:

- Display Operation start, progression, blocking, completion, and failure
- Record which Action produced which Transition
- Trace which Transition produced which Memory
- Display how a Memory changed a Belief
- Reverse-lookup the origin of ContextBundle values
- Display state before/after
- Assign a shared trace ID to one causal execution
- Replay or reconstruct past execution
- Answer “Why did this Belief change?”
- Record human approval, override, retry, rollback request, or annotation
- Present low-level internal data in human-readable units

Its central question is:

> What happened, why did it happen, and where may the human safely intervene?

---

## 5. Cockpit Metaphor

Blueprint Intelligence and Deterministic Machine Core together are the aircraft.

- Blueprint Intelligence resembles navigation, interpretation, and advanced flight assistance.
- Deterministic Machine Core resembles engines, control systems, and mechanical constraints.
- Control & Legibility Layer resembles the cockpit, instruments, warning systems, switches, and flight recorder.

A pilot does not need to continuously calculate fuel combustion inside an engine.

However, the pilot must be able to understand:

- Current status
- Direction
- Warnings
- Cause of abnormal behavior
- Available controls
- Expected result of an operation
- Whether a command was accepted
- Whether the aircraft can be returned to a safe state

Likewise, the creator of GM-AI should not need to reread every internal function to understand the current system behavior.

The system must provide a cockpit.

---

## 6. Core Design Principle

> **The Control & Legibility Layer does not own game state. It projects authoritative game state and causal history into a human-readable and human-operable form.**

This principle prevents the layer from becoming a second or third source of truth.

For example, a human may request a Belief correction through the Control Plane, but the Control Plane must not directly mutate the Belief store.

Correct flow:

```text
Human control input
→ formal Command / Action request
→ Machine Core validation
→ authoritative state mutation
→ Transition / trace emission
→ Control Plane result display
```

Incorrect flow:

```text
Human edits debug UI
→ debug UI directly rewrites Belief
→ no official Action
→ no Transition
→ no causal record
```

The cockpit may issue commands, but the aircraft systems remain responsible for executing them.

---

## 7. Required Properties

### 7.1 Human Legibility

A human must be able to understand the displayed information without reading raw source code.

Raw JSON, object dumps, and stack traces may be available as secondary evidence, but they are not sufficient as the primary interface.

The layer should translate internal data into concepts such as:

- Operation started
- Waiting for target selection
- Advisory adopted
- Action rejected
- Transition emitted
- Memory created
- Belief confidence increased
- Bundle rebuilt from these sources

---

### 7.2 Provenance

Every displayed result should have an identifiable origin.

Examples:

```text
Belief
← updated from Memory
← projected from Operation Transition
← caused by Action
← selected from Advisory
← generated from ContextBundle
```

If the origin cannot be determined, the system should display:

```text
Origin unknown
Trace incomplete
Not recorded by current instrumentation
```

It must not invent a plausible explanation.

---

### 7.3 Non-Ownership of Authoritative State

The Control Plane may cache display data, indexes, summaries, and trace projections.

It must not become the canonical owner of:

- World state
- Operation state
- Actor Memory
- Actor Belief
- ContextBundle
- Action validity
- Game rules

Authoritative ownership remains in the appropriate Machine Core or Blueprint component.

---

### 7.4 Formalized Human Intervention

Any human write operation should become an explicit, traceable command.

Examples:

- Approve advisory
- Reject advisory
- Retry Action
- Request rollback
- Add operator annotation
- Override target with reason
- Pause automatic progression
- Resume automatic progression

Each intervention should record:

- Who or what initiated it
- When it occurred
- Which trace it belongs to
- What was requested
- Whether validation accepted it
- What state changed
- Why it was performed

---

### 7.5 Optionality

GM-AI should still run without the graphical Control Plane.

The core game logic must not depend on a specific debug UI being open.

The architecture should permit:

```text
Headless Machine Core
+ trace/event output
+ optional Control & Legibility consumers
```

This supports testing, CLI operation, future Unity integration, server execution, and alternative monitoring interfaces.

---

### 7.6 Human-First Contract

AI may read and write through the Control Plane in the future.

However, the non-negotiable condition is:

> A human at the project owner’s technical level must be able to read, understand, and operate the Control Plane.

The target is not “only experts can understand it.”

The target is:

> **AI-operable, human-legible, human-governable.**

---

## 8. Functional Scope

The future Control & Legibility Layer may include the following functions.

### 8.1 Operation Timeline

Display:

- Operation created
- Operation started
- Operation progressed
- Current phase
- Current MiniGoal
- Blocking condition
- Completion
- Failure
- Cancellation
- Supersession by another Operation

---

### 8.2 Causal Trace

Trace a causal chain such as:

```text
ContextBundle
→ Intent
→ Advisory
→ adopted Action
→ Operation progression
→ Transition
→ Memory
→ Belief
→ next ContextBundle
```

---

### 8.3 State Diff

Display relevant state before and after an execution.

Example:

```text
Before:
operation.status = "started"
operation.target = null

After:
operation.status = "target_selected"
operation.target = "witness_a"
```

State diffs should be filtered to meaningful fields by default, with raw detail available when needed.

---

### 8.4 Provenance Lookup

Allow reverse lookup from a current value.

Example questions:

- Why does the detective believe the eastern route is unsafe?
- Which Memory contributed to this confidence value?
- Which Transition created that Memory?
- Which Action caused that Transition?
- Which player or AI decision selected that Action?

---

### 8.5 Replay and Reconstruction

The long-term design may allow:

- Replaying a trace
- Reconstructing the state at a prior event
- Comparing two runs
- Identifying nondeterministic divergence
- Reapplying a command to a copied state
- Producing a minimal reproduction case

Replay must not be claimed until the event and state model actually supports deterministic reconstruction.

---

### 8.6 Human Control Interface

Potential future controls:

- Pause
- Step execution
- Approve
- Reject
- Retry
- Cancel
- Roll back
- Branch from previous state
- Add annotation
- Mark an event as expected or suspicious

All controls should route through formal commands.

---

## 9. Suggested Trace Model

A future trace event may contain fields such as:

```text
event_id
trace_id
parent_event_id
event_type
timestamp
actor_id
operation_id
action_id
transition_id
source_component
initiator_type
initiator_id
summary
before
after
evidence_refs
result
failure_reason
schema_version
```

This is not yet a frozen schema.

The important early concepts are:

- One execution chain has a shared `trace_id`
- Events have stable identities
- Parent/causal relationships can be represented
- Human-readable summaries coexist with machine-readable evidence
- Schema evolution is versioned
- Trace data does not replace authoritative state

---

## 10. Minimum Viable Implementation

The minimum implementation should not begin as a large graphical dashboard.

The smallest useful implementation is an **Operation Trace Spine**.

### Minimum scope

1. Assign one `trace_id` to a meaningful execution chain.
2. Emit append-only Operation lifecycle events:
   - started
   - progressed
   - blocked
   - completed
   - failed
3. Record the Action that caused each Operation event when known.
4. Record a small before/after diff for relevant Operation fields.
5. Provide a simple human-readable debug output:
   - text log
   - CLI inspector
   - JSON trace file plus formatted summary
6. Ensure the trace store is not the authoritative Operation state.
7. Add tests proving that instrumentation does not change game behavior.

A minimal trace could look like:

```text
TRACE 2026-07-25-001

[1] Advisory adopted
    actor: detective
    action: choose_first_inquiry_target

[2] Action validated
    result: accepted

[3] Operation progressed
    operation: first_inquiry
    before: started
    after: target_selected
    target: witness_a

[4] Transition emitted
    transition: inquiry_target_selected
```

This alone would already make Operation behavior substantially easier to follow.

---

## 11. What Should Not Be Implemented First

The following should not be included in the first implementation:

- Full graphical cockpit
- Complete Memory provenance
- Complete Belief provenance
- ContextBundle field-by-field origin graph
- General rollback
- Deterministic replay of the entire world
- Direct manual state editing
- AI-generated explanations without evidence
- A new universal event framework replacing all current systems at once

These are later extensions.

Trying to implement all of them during the first large refactoring would increase risk and make the Control Plane itself another source of complexity.

---

## 12. Recommended Timing for Session 60

### Current Session 60-0

For Session 60-0, conceptual organization is sufficient.

The current goal should be to establish the architectural constraint:

> Future refactoring must make important Operation behavior observable and traceable without requiring a human to reread the entire implementation.

Session 60-0 should define:

- Why the Human Control Plane exists
- What it owns and does not own
- Which causal relationships must eventually be traceable
- Which Operation lifecycle events are important
- Which current behaviors must remain invariant
- Where trace hooks can be added without creating a second source of truth

No full implementation is required yet.

---

### Early Session 60

The first implementation should occur after:

1. The current Operation responsibility map is complete.
2. Current behavior and invariants are documented.
3. The refactoring boundary is chosen.
4. The Operation lifecycle vocabulary is stabilized enough to emit meaningful events.

At that point, the minimal Operation Trace Spine should be introduced either:

- immediately before moving Operation responsibilities, so it observes the old and new paths, or
- as the first small step of the Operation refactor, before structural changes become large.

The preferred strategy is:

```text
Understand current flow
→ define invariants
→ add minimal observation seams
→ refactor one boundary
→ compare trace and tests
→ continue
```

This makes the Control Plane a safety instrument for the refactoring rather than a separate feature added afterward.

---

## 13. Implementation Placement

The Control & Legibility Layer should be positioned as a cross-cutting infrastructure area, not inside the player HUD and not inside one specific Operation implementation.

Conceptually:

```text
src/
  blueprint_intelligence/
  machine_core/
  control_plane/
    trace/
    inspection/
    commands/
    projections/
```

The exact package structure should not be decided before the Session 60 responsibility map is complete.

For the minimum implementation, only a narrow portion may be required:

```text
control_plane/
  operation_trace.py
```

or an equivalent package aligned with the existing project layout.

The Machine Core emits structured facts.

The Control Plane formats, indexes, and displays those facts.

The player HUD may later consume selected Control Plane projections, but the player HUD should not be the canonical Control Plane.

---

## 14. Relationship to Existing HUD and Intelligence Panel

The existing HUD is primarily player-facing.

The Control & Legibility Layer is initially:

- developer-facing
- operator-facing
- game-master-facing
- scenario-designer-facing

Possible future interfaces include:

```text
Player HUD
Intelligence Panel
Developer Console
Operation Inspector
Causal Trace Viewer
State Diff Viewer
Replay Viewer
```

Some explanations may later become part of gameplay.

For example, a player-facing Intelligence Panel might expose:

- Why an RC recommends a particular action
- Which past Memory influenced the recommendation
- Whether the RC is uncertain
- Which Operation goal is currently blocked

However, development diagnostics and player-visible narrative explanation should remain separable projections.

---

## 15. Architectural Invariants

The following invariants should guide future implementation:

1. Control Plane observation must not change gameplay outcome.
2. Control Plane data must not become the authoritative game state.
3. Human write operations must pass through formal validation.
4. Trace records must identify incomplete or unknown provenance honestly.
5. Rebuilding the HUD or inspector must not emit gameplay mutations.
6. Duplicate refreshes must not create duplicate causal events.
7. Actor separation must be preserved in all traces.
8. Save/load behavior must remain consistent with or without the inspector.
9. Trace schema changes must be versioned.
10. Every displayed causal explanation must be grounded in recorded evidence.

---

## 16. Development Value

The Human Control Plane supports more than debugging.

It may become a central GM-AI capability because it enables:

- Safe AI-assisted development
- Human supervision of complex internal reasoning
- Explainable RC behavior
- Reproducible bug reports
- Refactoring confidence
- Scenario authoring support
- Player-visible character reasoning
- Controlled human intervention
- Future AI-generated code with human governance
- Separation between system capability and human cognitive load

The project does not need to limit its internal capability to what one human can memorize.

Instead, it must limit the **control interface complexity** to what one human can understand and operate.

---

## 17. Final Design Statement

> GM-AI uses Blueprint Intelligence to interpret and propose, and a Deterministic Machine Core to validate and execute.  
> A Human Control Plane projects their behavior into a traceable, explainable, and controllable form.  
> The Human Control Plane does not become a third source of game truth. It is the cockpit through which a human can understand, supervise, and safely operate an increasingly complex system.

In one line:

> **Do not keep GM-AI small enough to fit inside the creator’s head; build a cockpit that keeps the creator in control as GM-AI grows.**
