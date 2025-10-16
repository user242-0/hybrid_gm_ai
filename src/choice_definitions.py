from src.choice_model import Choice

import yaml
import numpy as np
from pathlib import Path

RULES_DIR = Path("data/rules")

choice_definitions = {
    "戦う":            {"axis": "red", "value": 250},
    "戦わない":        {"axis": "red","value": 180},
    "ただ、受け入れる": {"axis": "red","value": 180},
    "攻撃する":        {"axis": "blue",  "value": 200},
    "swing_sword":      {"axis": "blue",  "value": 200},
    "switch_character": {"axis": "green", "value": 255},
    "石像に話す":      {"axis": "blue",  "value": 80},
    "探索する":        {"axis": "blue",  "value": 80},
    "石像に話す（クールダウン）":{"axis": "blue",  "value": 100},
    "進む":             {"axis": "blue",  "value": 100},
    "休む":             {"axis": "blue",  "value": 100},
    "感情を設定する":   {"axis": "green", "value": 150},  # 新規追加：プレイヤーの心を設定する緑コマンド
}

def get_available_choices(actor, game_state):
    from src.requirements_checker import RequirementsChecker
    
    checker = RequirementsChecker(game_state, actor)

    available = []
    from src.action_definitions import actions
    for key, meta in choice_definitions.items():
        act_meta = actions.get(key, {})

        # NPC／プレイヤーの区分をチェック
        available_to = act_meta.get("available_to")
        if actor.is_npc and available_to and "npc" not in available_to:
            continue
        if not actor.is_npc and available_to and "player" not in available_to:
            continue

        
        
        # Choice インスタンスを生成
        choice = Choice(
            label=key,
            action_key=key,
            emotion_axis=meta.get("emotion_axis", meta.get("axis")),  # "red"|"green"|"blue"
            emotion_value=meta.get("emotion_value", meta.get("value", 128)),
            requirement_keys=act_meta.get("requirements")
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