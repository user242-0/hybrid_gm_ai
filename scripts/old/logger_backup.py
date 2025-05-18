import json
from datetime import datetime
import os


def log_action(actor, action, target, location, result, game_state):

    current_time = datetime.now()

    # 明示的に初期化
    talk_count = None
    interval = None
    talk_situation = None

    if action in ["石像に話す", "石像に話す（クールダウン）"]:

        # game_state経由で安全に値を取得（推奨）
        talk_count = game_state.get("talk_count")
        interval = game_state.get("interval")
        talk_situation = game_state.get("talk_situation", ["normal"])

        

    # 以下デバッグ用プリント追加
    # print(f"[DEBUG] action: {action}, talk_count: {talk_count}, interval: {interval}, talk_situation: {talk_situation}")

    log_entry = {
        "timestamp": current_time.isoformat(),
        "actor": actor,
        "action": action,
        "target": target,
        "location": location,
        "result": result,
        "talk_count": talk_count,
        "interval": interval,
        "talk_situation": talk_situation
    }

    os.makedirs("data/logs", exist_ok=True)

    with open("data/logs/gameplay_log_latest.json", "a", encoding="utf-8") as logfile:
        logfile.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
