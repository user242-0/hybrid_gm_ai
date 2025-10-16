# src/gmcore/context_eval.py
from typing import Protocol, Dict, Any

class ContextEvaluator(Protocol):
    def evaluate(self, game_state: Dict[str,Any]) -> Dict[str,float]:
        ...

class BaselineEvaluator:
    def evaluate(self, game_state):
        # スタブ：必要なら後で本実装に差し替え
        return {"salience": 0.5, "novelty": 0.5}
