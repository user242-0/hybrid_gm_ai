from random import choices as rnd_choices
from src.requirements_checker import RequirementsChecker

def select_action(rc_char, game_state, available):
    checker = RequirementsChecker(game_state, rc_char)

    # ❶ フィルタリング段階で switch_character を除外
    green = [c for c in available
               if c.emotion_axis == "green"
               and c.is_available(checker)
               and not (game_state["input_pending"] and c.action_key == "switch_character")]

    if not green:
        return None

    weights = [c.emotion_value for c in green]
    return rnd_choices(green, weights=weights, k=1)[0]