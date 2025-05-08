import random
from src.requirements_checker import RequirementsChecker

def select_action(rc_char, game_state, choices):
    checker = RequirementsChecker(game_state, rc_char)
    green = [c for c in choices
              if c.emotion_axis == "green" 
              and c.is_available(checker)]
    return random.choice(green) if green else None