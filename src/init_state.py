from pathlib import Path
import yaml

from src.character_status import CharacterStatus


PACK_DIR = Path(__file__).parent.parent / "data" / "director" / "packs"


def _load_pack(pack_id: str) -> dict:
    """パックYAMLを読み込む（registry.pyと同等の機能を循環インポート回避のため直接実装）"""
    pack_path = PACK_DIR / f"{pack_id}.yml"
    with open(pack_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def init_game_state(pack_id: str = "cop_trickster"):
    """
    パックを参照してgame_stateを組み立てる。
    パックはデータ（roles/locations/targets）を持ち、この関数が構造を組み立てる責務を持つ。
    """
    pack = _load_pack(pack_id)
    roles = pack.get("roles", {})
    locations = pack.get("locations", {})
    targets = pack.get("targets", {})

    # --- キャラクター作成 ---
    protagonist_data = roles.get("protagonist", {})
    antagonist_data = roles.get("antagonist", {})

    protagonist_name = protagonist_data.get("name", "刑事")
    antagonist_name = antagonist_data.get("name", "愉快犯")

    protagonist = CharacterStatus(protagonist_name, is_rc=True, is_npc=False)
    antagonist = CharacterStatus(antagonist_name, is_rc=True, is_npc=True)
    antagonist.equipped_weapon = {"weapon_type": "small_knife", "name": "小さいナイフ"} 

    # --- 関係性タグ設定 ---
    # 刑事から見た愉快犯
    antagonist.add_label_from(protagonist_name, "容疑者")
    antagonist.add_label_from(protagonist_name, "追跡対象")
    # 愉快犯から見た刑事
    protagonist.add_label_from(antagonist_name, "追手")
    protagonist.add_label_from(antagonist_name, "興味深い存在")

    # --- ロケーション / ターゲット ---
    current_location = locations.get("default", "事件現場")
    current_target = targets.get("default", antagonist_name)

    # --- actor別emotion初期化 ---
    # CharacterStatusの初期emotion_colorを使用
    emotions_by_actor = {
        protagonist.name: {
            "R": protagonist.emotion_color[0],
            "G": protagonist.emotion_color[1],
            "B": protagonist.emotion_color[2],
        },
        antagonist.name: {
            "R": antagonist.emotion_color[0],
            "G": antagonist.emotion_color[1],
            "B": antagonist.emotion_color[2],
        },
    }

    return {
        "party": {
            protagonist.name: protagonist,
            antagonist.name: antagonist,
        },
        "party_map": {
            protagonist.name: protagonist,
            antagonist.name: antagonist,
        },
        "active_char": protagonist,
        "allow_ai_to_seize_control": True,
        "running": True,
        "input_pending": False,
        "use_gui": True,
        "auto_step_pending": False,
        "events": {},
        "current_location": current_location,
        "current_target": current_target,
        "has_enemy": True,
        "enemy": antagonist,
        "available_locations": locations.get("available", [current_location]),
        "pack_id": pack_id,
        "emotions_by_actor": emotions_by_actor,
    }
