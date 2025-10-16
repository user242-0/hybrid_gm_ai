# exploration.pyから関数をインポート
from .exploration import explore_location, move_forward, rest_with_event, determine_next_location, generate_dynamic_event, generate_location_event

# combat.pyから関数をインポート
from .combat import engage_combat, avoid_combat, accept_attack, perform_attack,swing_sword, present_event_choices, pre_combat_moment

# npc_interactions.pyから関数をインポート（存在する場合）
from .npc_interactions import talk_to_statue, talk_to_statue_with_cooldown, generate_omni_controlled_response, npc_speak, npc_speak_and_log
# utility.pyから共通関数をインポート（存在する場合）
from .utility import generate_flavor_text, generate_card_and_print, choose_event_parameters