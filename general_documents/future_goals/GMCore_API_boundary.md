# GMCore API boundary

## Status

Future design note. This API is not used by the current runtime.

The former `src/gmcore/context_eval.py` was a small stub discovered as a
namespace package by setuptools even though no runtime code or tests imported
it. It was moved out of `src/` on 2026-06-19 to avoid presenting an unused API
as shipped runtime functionality.

## Proposed boundary

A future GMCore layer may expose context evaluation behind a protocol:

```python
from typing import Any, Protocol


class ContextEvaluator(Protocol):
    def evaluate(self, game_state: dict[str, Any]) -> dict[str, float]:
        ...
```

The original baseline implementation returned fixed placeholder values:

```python
class BaselineEvaluator:
    def evaluate(self, game_state):
        return {"salience": 0.5, "novelty": 0.5}
```

Before reintroducing this under `src/`, define:

1. Which runtime component owns context evaluation.
2. The required input state and stable output schema.
3. How it relates to `src/datalab/emitters/emotion_emitter.py`.
4. Tests covering real consumers rather than a standalone placeholder.
