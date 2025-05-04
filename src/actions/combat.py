from src.character_status import CharacterStatus

def engage_combat(character_status, game_state, enemy_character_status=None):
    print(f"{character_status.name}が敵との戦闘を開始します……")

    # ① どの形式で渡された敵でも同じ変数 enemy_obj にまとめる
    enemy_obj = enemy_character_status or game_state.get("enemy")

    # ② 形式を判定して HP・攻撃力・名前を取り出す
    if isinstance(enemy_obj, CharacterStatus):
        enemy_hp            = enemy_obj.hp
        enemy_attack_power  = enemy_obj.attack_power
        enemy_name          = enemy_obj.name
    else:                                     # dict 互換なら従来通り
        enemy_hp            = enemy_obj["hp"]
        enemy_attack_power  = enemy_obj["attack_power"]
        enemy_name          = enemy_obj["name"]

    # ③ プレイヤー側の攻撃力
    attack_power = character_status.attack_power if character_status.equipped_weapon else 1

    # ④ 戦闘ループ
    while character_status.hp > 0 and enemy_hp > 0:
        enemy_hp -= attack_power
        print(f"{enemy_name}に{attack_power}のダメージを与えた！ (敵HP: {enemy_hp})")

        if enemy_hp <= 0:
            print(f"{enemy_name}を倒しました！")
            game_state["has_enemy"] = False
            break

        character_status.hp -= enemy_attack_power
        print(f"{enemy_name}から{enemy_attack_power}のダメージを受けた！ (HP: {character_status.hp})")

    # ⑤ HP を書き戻す（敵がオブジェクトなら）
    if isinstance(enemy_obj, CharacterStatus):
        enemy_obj.hp = max(enemy_hp, 0)

    return "勝利" if enemy_hp <= 0 else "敗北"


def avoid_combat(character_status, game_state):
    print(f"{character_status.name}は戦闘を避けました。")
    character_status.change_status(hp_change=-5, stamina_change=-10)
    print("体力とスタミナが少し減りました。")
    return "逃走成功"

def accept_attack(character_status, game_state):
    enemy_obj =  game_state.get("enemy", {"name": "謎の敵", "attack_power": 5})
    damage = enemy_obj.attack_power
    print(f"{character_status.name}は無抵抗で{enemy_obj.name}の攻撃を受けました！")
    character_status.change_status(hp_change=-damage)
    print(f"{damage}のダメージを受けました。(HP残り：{character_status.hp})")
    return f"{damage}ダメージを受けた"

def perform_attack(character_status, game_state, target="敵"):
    print(f"{character_status.name}が{target}を攻撃しました（仮）")
    # 実装は後ほど！

    # 常に成功するととりあえず仮定
    return "成功"

def present_event_choices(event_type):
    print("\n行動を選択してください:")

    if event_type == "戦闘":
        choices = {
            "1": {"description": "積極的に攻撃する（リスク大、リターン大）", "hp": -20, "stamina": -15, "attack": +5},
            "2": {"description": "慎重に防御する（リスク小、リターン小）", "hp": -5, "stamina": -5, "attack": 0},
            "3": {"description": "逃げる（イベント終了）", "hp": 0, "stamina": -10, "attack": 0}
        }
    elif event_type == "探索":
        choices = {
            "1": {"description": "隅々まで探索（時間をかける）", "hp": -5, "stamina": -20, "attack": 0},
            "2": {"description": "軽く探索する（短時間）", "hp": 0, "stamina": -5, "attack": 0},
            "3": {"description": "探索をやめる", "hp": 0, "stamina": 0, "attack": 0}
        }
    elif event_type == "謎解き":
        choices = {
            "1": {"description": "積極的に謎を解く（スタミナ消費）", "hp": 0, "stamina": -15, "attack": 0},
            "2": {"description": "謎解きを諦める", "hp": 0, "stamina": 0, "attack": 0}
        }
    else:  # 会話
        choices = {
            "1": {"description": "積極的に話を聞く（スタミナ消費）", "hp": 0, "stamina": -10, "attack": 0},
            "2": {"description": "会話を終える", "hp": 0, "stamina": 0, "attack": 0}
        }

    for key, choice in choices.items():
        print(f"{key}. {choice['description']}")

    selected = input("\n番号を選択してください: ")
    return choices.get(selected, None)

 # present_event_choices は探索イベントでも使う可能性がある場合、「④utility.py」に入れる選択肢もあります。

 # NPCモーメント
def pre_combat_moment(player, enemy_npc, game_state):
    moment_actions = ["戦う", "戦わない", "ただ、受け入れる"]

    print(f"\n【緊迫のモーメント】{enemy_npc.name}があなたに敵意を向けています……")
    print("あなたはどうしますか？")
    for idx, act in enumerate(moment_actions, 1):
        print(f"{idx}. {act}：{actions[act]['description']}")

    choice = input("番号を選択してください（1～3）: ")

    try:
        selected_action_name = moment_actions[int(choice)-1]
    except (IndexError, ValueError):
        print("無効な入力です。何もしませんでした。")
        return

    # アクション実行
    action_details = actions[selected_action_name]
    function_to_execute = action_details["effects"]["function"]
    args = action_details["effects"]["args"]

    result = function_to_execute(player, game_state, enemy_character_status=enemy_npc) if selected_action_name == "戦う" else function_to_execute(player, game_state)

    print(f"行動結果：{result}")

    # ログに記録
    log_action(
        actor=player.name,
        action=selected_action_name,
        target=enemy_npc.name,
        location=player.location,
        result=result,
        game_state=game_state
    )