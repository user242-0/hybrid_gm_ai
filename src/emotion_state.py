## src/emotion_state.py
from dataclasses import dataclass, field
from typing import Tuple, Literal
from time import time
from .emotion_math import clip_rgb, project_nlc_to_lc, expand_lc_to_nlc

Color = Tuple[int, int, int]
Source = Literal["player_input", "inferred", "derived"]

@dataclass
class EmotionState:
    """
    NLC（nonlinear）を“真”として保持し、LC（linear）はUI用の射影をキャッシュ。
    """
    nonlinear: Color = (127, 127, 255)   # R,G,B 独立
    linear:    Color = (127, 127, 255)   # R≥G≥B を満たす UI/判定用
    source:    Source = "inferred"
    confidence: float = 0.8
    updated_at: float = field(default_factory=lambda: time())

    def set_linear(self, rgb: Color, *, update_nonlinear: bool = True):
        self.linear = clip_rgb(rgb)
        self.updated_at = time()
        self.source = "player_input"
        if update_nonlinear:
            self.nonlinear = expand_lc_to_nlc(self.linear, self.confidence)

    def set_nonlinear(self, rgb: Color, *, update_linear: bool = True, source: Source = "inferred"):
        self.nonlinear = clip_rgb(rgb)
        self.updated_at = time()
        self.source = source
        if update_linear:
            self.linear = project_nlc_to_lc(self.nonlinear, self.confidence)
