import json
from datetime import datetime
import os

# 会話履歴を保持する辞書を追加
conversation_history = {}

def classify_talk_situation(talk_count, interval):
    hour = datetime.now().hour

    if talk_count == 1:
        return "first_time"
    elif interval is not None and interval < 30:
        return "repeated_short_interval"
    elif hour >= 23 or hour <= 4:
        return "late_night"
    else:
        return "normal"

def log_action(actor, action, target, location, result):
    global conversation_history

    current_time = datetime.now()

    talk_count = None
    interval = None
    talk_situation = None

    if action in ["石像に話す", "石像に話す（クールダウン）"]:
        key = f"{actor}_{target}"

        if key in conversation_history:
            last_talk_time, count = conversation_history[key]
            interval = (current_time - last_talk_time).total_seconds()
            talk_count = count + 1
        else:
            talk_count = 1

        # 状況分類を行う
        talk_situation = classify_talk_situation(talk_count, interval)

        conversation_history[key] = (current_time, talk_count)

    log_entry = {
        "timestamp": current_time.isoformat(),
        "actor": actor,
        "action": action,
        "target": target,
        "location": location,
        "result": result,
        "talk_count": talk_count,
        "interval": interval,
        "talk_situation": talk_situation  # ← 追加
    }

    os.makedirs("data/logs", exist_ok=True)

    with open("data/logs/gameplay_log_blue_0425_latest.json", "a", encoding="utf-8") as logfile:
        logfile.write(json.dumps(log_entry, ensure_ascii=False) + "\n")