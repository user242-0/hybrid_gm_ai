from src.choice_model import Choice

import yaml
import numpy as np
from pathlib import Path

RULES_DIR = Path("data/rules")

# --- 旧キー互換マップ（日本語 → 英語action_id） ---
# ログやセーブデータに日本語キーが残っている場合の変換用
LEGACY_KEY_MAP = {
    "探索する": "explore",
    "進む": "move_forward",
    "休む": "rest",
    "攻撃する": "attack",
    "戦う": "engage_combat",
    "戦わない": "avoid_combat",
    "ただ、受け入れる": "accept_attack",
    "石像に話す": "talk_to_statue",
    "石像に話す（クールダウン）": "talk_to_statue_cooldown",
    "NPCが話す": "npc_speak",
    "カード生成イベント": "generate_card",
    "感情を設定する": "set_emotion",
}


def resolve_action_key(key: str) -> str:
    """旧キー（日本語）を新action_id（英語）に変換"""
    return LEGACY_KEY_MAP.get(key, key)


def get_available_choices(actor, game_state):
    """
    action_definitionsからUI表示可能なアクションを自動生成。
    - ui_visible=True のもののみ表示
    - requirements_checker を通るもののみ
    - heartからemotion_axis/valueを取得
    """
    from src.requirements_checker import RequirementsChecker
    from src.action_definitions import get_action_specs

    checker = RequirementsChecker(game_state, actor)
    specs = get_action_specs()

    available = []
    for action_id, spec in specs.items():
        # UI非表示はスキップ
        if not spec.ui_visible:
            continue

        # NPC／プレイヤーの区分をチェック
        available_to = spec.available_to or []
        if actor.is_npc and "npc" not in available_to:
            continue
        if not actor.is_npc and "player" not in available_to:
            continue

        # heartからemotion情報を取得
        heart = spec.heart or {"axis": "green", "value": 50}
        emotion_axis = heart.get("axis", "green")
        emotion_value = heart.get("value", 50)

        # Choice インスタンスを生成（labelとaction_keyを分離）
        choice = Choice(
            label=spec.label,
            action_key=action_id,  # 英語の内部ID
            emotion_axis=emotion_axis,
            emotion_value=emotion_value,
            requirement_keys=spec.requirements
        )

        # 実行条件を満たすか
        if choice.is_available(checker):
            available.append(choice)

    return available

##以下、features.yaml,行動.yaml(W_action含む)を実装した時に追加

def load_features():
    y = yaml.safe_load((RULES_DIR / "features.yaml").read_text(encoding="utf-8"))
    return [f["id"] for f in y["features"]], y.get("rgb_mode", "floats_0_1")

def load_action_def(name: str):
    y = yaml.safe_load((RULES_DIR / "actions" / f"{name}.yaml").read_text(encoding="utf-8"))
    return y  # {base_rgb, mixing{alpha,beta,gamma}, features, W_action{R,G,B}, ...}

def compute_ctx_rgb(action_def, f_context_vec):
    W = np.stack([action_def["W_action"]["R"],
                  action_def["W_action"]["G"],
                  action_def["W_action"]["B"]], axis=0)  # 3×K
    return (W @ np.array(f_context_vec)).tolist()

def mix_rgb(base, heart, ctx, mixing):
    v = (np.array(base)*mixing["alpha"] +
         np.array(heart)*mixing["beta"] +
         np.array(ctx)*mixing["gamma"])
    return np.clip(v, 0.0, 1.0).tolist()