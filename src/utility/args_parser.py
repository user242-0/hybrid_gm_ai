from src.utility.targeting import prompt_target_rc

def parse_args(action_def, actor, game_state):
    resolved = []
    for token in action_def.get("args_template", []):
        if token == "<target_name>":
            resolved.append(prompt_target_rc(actor, game_state))
        else:
            resolved.append(token)
    return resolved