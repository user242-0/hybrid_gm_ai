"""GameContext: simulation.py のグローバル変数を一元管理するコンテキストクラス"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from src.utility.config_loader import is_hud_debug_enabled

if TYPE_CHECKING:
    from src.scheduler import Scheduler
    from src.ui.action_pipeline import ActionPipeline
    from director.director import Director


@dataclass
class GameContext:
    """
    ゲーム全体の状態を保持するコンテキスト。

    従来 simulation.py でモジュールレベルのグローバル変数として
    散在していたものを一箇所にまとめる。
    """

    # 必須
    scheduler: Scheduler
    game_state: dict
    cfg: dict

    # オプション（Director関連）
    director: Director | None = None
    director_world: dict | None = None
    director_hud: Any | None = None  # DirectorHUD (optional import)
    pipeline: ActionPipeline | None = None

    # 状態フラグ
    auto_enabled: bool = False

    # HUD用キャッシュ
    current_actions: list[tuple[str, str, int]] = field(default_factory=list)

    # コールバック（オプション）
    ui_refresh: Callable[[], None] | None = None

    # 定数
    AUTO_STEP_INTERVAL_SECONDS: float = 0.5

    def set_auto(self, enabled: bool) -> None:
        """自動ステップモードの切り替え"""
        import time
        self.auto_enabled = bool(enabled)
        if self.auto_enabled:
            self.game_state["last_auto_ts"] = time.monotonic() - self.AUTO_STEP_INTERVAL_SECONDS
        if self.director_hud is not None:
            self.director_hud.set_auto_enabled(self.auto_enabled)
        state = "on" if self.auto_enabled else "off"
        print(f"[RC_AI] auto={state}")

    def request_auto_step(self) -> None:
        """次のループで自動ステップを1回実行するようリクエスト"""
        self.game_state["auto_step_pending"] = True

    def resolve_world(self) -> dict | None:
        """director_world または game_state['world'] を返す"""
        if isinstance(self.director_world, dict):
            return self.director_world
        world = self.game_state.get("world")
        if isinstance(world, dict):
            return world
        return None

    def bump_hud_cache_rev(self, reason: str | None = None) -> None:
        """HUDキャッシュのリビジョンをインクリメント"""
        self.game_state["hud_cache_rev"] = self.game_state.get("hud_cache_rev", 0) + 1
        if reason and is_hud_debug_enabled():
            print(f"[HUD_DEBUG] bump reason={reason} rev={self.game_state['hud_cache_rev']}")

    def update_microgoal(self, micro_goal: str | None) -> None:
        """マイクロゴールを更新し、変化があればHUDキャッシュを更新"""
        previous = self.game_state.get("director_micro_goal")
        self.game_state["director_micro_goal"] = micro_goal
        if previous != micro_goal:
            self.bump_hud_cache_rev(reason="microgoal_change")
