# conversation_manager.py
from datetime import datetime

class ConversationManager:
    def __init__(self):
        self.conversation_history = {}

    def update_conversation(self, actor, target):
        key = f"{actor}_{target}"
        now = datetime.now().isoformat()

        if key in self.conversation_history:
            previous = self.conversation_history[key]
            interval = (datetime.fromisoformat(now) - datetime.fromisoformat(previous["last_talk_time"])).total_seconds()
            talk_count = previous["talk_count"] + 1
        else:
            interval = None
            talk_count = 1

        self.conversation_history[key] = {
            "last_talk_time": now,
            "talk_count": talk_count,
            "interval": interval,
            "talk_situation": self.classify_talk_situation(talk_count, interval)
        }

    def get_talk_count(self, actor, target):
        key = f"{actor}_{target}"
        return self.conversation_history.get(key, {}).get("talk_count", 0)

    def get_talk_situation(self, actor, target):
        key = f"{actor}_{target}"
        return self.conversation_history.get(key, {}).get("talk_situation", ["normal"])
    
    def get_interval(self, actor, target):
        key = f"{actor}_{target}"
        return self.conversation_history.get(key, {}).get("interval", None)

    def classify_talk_situation(self, talk_count, interval):
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
