# src/datalab/registry/action_registry.py
def normalize_action(key: str, args: list[str] | None = None) -> str:
    table = {
        "swing_sword": "swing_sword",
        "攻撃する": "attack",
        "石像に話す": "talk_to_statue",
        "石像に話す（クールダウン）": "talk_to_statue",
        # 必要に応じて追加
    }
    # ← 未定義なら「元のキー」を返す（Noneは返さない）
    return table.get(key, key)
