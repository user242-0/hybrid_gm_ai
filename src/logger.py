import json
from datetime import datetime
import os

# 会話履歴を保持する辞書をグローバルで管理
conversation_history = {}

def classify_talk_situation(talk_count, interval):
    situations = []
    hour = datetime.now().hour

    if talk_count == 1:
        situations.append("first_time")
    if interval is not None and interval < 30:
        situations.append("repeated_short_interval")
    if hour >= 23 or hour <= 4:
        situations.append("late_night")

    if not situations:
        situations.append("normal")

    return situations

def log_action(actor, action, target, location, result):
    global conversation_history

    current_time = datetime.now()

    # 明示的に初期化
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
            interval = None

        talk_situation = classify_talk_situation(talk_count, interval)
        conversation_history[key] = (current_time, talk_count)

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
