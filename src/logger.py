import json
from datetime import datetime
import os

def log_action(actor, action, target, location, result):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "actor": actor,
        "action": action,
        "target": target,
        "location": location,
        "result": result
    }
    
    os.makedirs("data/logs", exist_ok=True)
    with open("data/logs/gameplay_red_log_v2.json", "a", encoding="utf-8") as logfile:
        logfile.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
