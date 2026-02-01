"""Action specification models for unified action lookup."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ActionSpec:
    id: str
    label: str
    description: Optional[str] = None
    time_min: int = 0
    emotion_delta: Optional[Dict[str, int]] = None
    tags: Optional[List[str]] = None
    requirements: Any = None
    args_template: Optional[List[str]] = None
    available_to: Optional[List[str]] = None
    effects: Optional[List[Dict[str, Any]]] = None
    function: Optional[Callable[..., Any]] = None
    id_aliases: List[str] = field(default_factory=list)
    ui_visible: bool = True  # UI選択肢に表示するか
    heart: Optional[Dict[str, Any]] = None  # {axis: "red"|"green"|"blue", value: 0-255}

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "time_min": self.time_min,
            "emotion_delta": self.emotion_delta,
            "tags": self.tags,
            "requirements": self.requirements,
            "args_template": self.args_template,
            "available_to": self.available_to,
            "effects": self.effects,
            "function": self.function,
            "id_aliases": self.id_aliases or None,
            "ui_visible": self.ui_visible,
            "heart": self.heart,
        }
        return {key: value for key, value in data.items() if value is not None}
