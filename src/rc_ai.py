from random import choices as rnd_choices
from src.requirements_checker import RequirementsChecker

def select_action(rc_char, game_state, available):
    checker = RequirementsChecker(game_state, rc_char)

    # ❶ switch_character は最優先（input_pending 中でも許可）
    for c in available:
        if c.action_key == "switch_character" and c.is_available(checker):
            return c

    # ❷ 通常時は緑から抽選
    green = [c for c in available
             if c.emotion_axis == "green" and c.is_available(checker)]

    if not green:
        return None

    weights = [c.emotion_value for c in green]
    return rnd_choices(green, weights=weights, k=1)[0]