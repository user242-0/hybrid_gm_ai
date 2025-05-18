from random import choice as rnd
from src.requirements_checker import RequirementsChecker

def select_action(rc_char, game_state, choices):
    checker = RequirementsChecker(game_state, rc_char)

    # ❶ フィルタリング段階で switch_character を除外
    green = [c for c in choices
             if c.emotion_axis == "green"
             and c.is_available(checker)
             and not (game_state["input_pending"] and c.action_key == "switch_character")]

    return rnd(green) if green else None