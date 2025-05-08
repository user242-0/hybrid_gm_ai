from src.utility.targeting import prompt_target_rc

def parse_args(action_def, player, game_state):
    resolved = []
    for token in action_def.get("args_template", []):
        if token == "<target_name>":
            resolved.append(prompt_target_rc(game_state))
        else:
            resolved.append(token)
    return resolved