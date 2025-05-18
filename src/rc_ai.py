from random import choice as rnd
from src.requirements_checker import RequirementsChecker

def select_action(rc_char, game_state, choices):
    checker = RequirementsChecker(game_state, rc_char)

    # ❶ フィルタリング段階で switch_character を除外
    green = [c for c in choices
               if c.emotion_axis == "green"
               and c.is_available(checker)
               and not (game_state["input_pending"] and c.action_key == "switch_character")]

    if not green:
        return None

    max_val = max(c.emotion_value for c in green)
    top = [c for c in green if c.emotion_value == max_val]
    return rnd(top)