import time
from logger import log_action  # ログ関数をインポートする例
import random 
import openai
import os
from dotenv import load_dotenv
import json

# .envから環境変数を読み込む
load_dotenv()

# .env内にあるAPIキーを使う
openai.api_key = os.getenv("OPENAI_API_KEY")

# クールダウン管理の状態保持（グローバル変数かクラス内の属性が理想）
cooldown_status = {}



# 石像の固定セリフ
fixed_dialogue_omni = {
"石像に話す": "よくぞここまで来た。我が名はオムニ。この地に訪れし者よ、何を求めてここに来た？"
}

fixed_dialogue_omni_2 = {
"オムニ：「今は語るべきことがない。時を置いて訪れよ。」"
}

fixed_dialogue = {
    "敵対的NPC": {
        "combat_start": "覚悟しろ、ここがお前の墓場だ！",
        "combat_win": "たったそれだけか？",
        "combat_lose": "くっ、この私が……！"
    },
    "NPC戦士": {
        "greeting": "共に戦えることを光栄に思う。",
        "farewell": "次の戦いでまた会おう。"
    }
}

# フレーバーテキスト生成関数
# 簡単なキャッシュ
flavor_text_cache = {}

def generate_flavor_text(action, talk_situation, location):
    time_description = "深夜（夜間・真夜中）" if "late_night" in talk_situation else "昼間（通常時間帯）"
    
    prompt = f"""
    あなたはゲーム内の短めのフレーバーテキストを生成するAIです。

    場所：{location}（例：祭壇、洞窟など）
    時間帯：{time_description}
    状況：「{', '.join(talk_situation)}」（例：深夜、短時間の連続会話など）
    アクション：{action}

    深夜の描写の場合、「朝」「昼」「陽光」「小鳥のさえずり」など、夜間には存在しない要素は絶対に含めず、月光や暗闇など、夜にふさわしい要素のみを使用してください。

    アクションに応じた100文字以内の簡潔で矛盾のない描写を生成してください。
    セリフやストーリー要素は一切含めないでください。

    アクションごとの具体的な描写例：
    - 「進む」：前方の道や周囲の情景の変化を描写。
    - 「休む」：キャラクターが休息をとる際の周囲の状況や空気感を描写。
    - 「攻撃する」：戦闘の緊迫感や敵との対峙の状況を描写。
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたは指定されたアクション・場所・時間帯・状況に矛盾のない短い情景描写を生成するAIです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content




##　実際のアクションリスト
def explore_location(character_status, game_state):
    action = "探索する"
    location = game_state.get('location', '未知の場所')
    talk_situation = game_state.get('talk_situation', ['normal']) 
    
    flavor_text = generate_flavor_text(action, talk_situation, location)
    print(flavor_text)

    return "成功"



def move_forward(character_status, game_state):
    action = "進む"
    location = game_state.get('location', '未知の場所')
    talk_situation = game_state.get('talk_situation', ['normal'])

    flavor_text = generate_flavor_text(action, talk_situation, location)
    print(f"{character_status.name}は進みます……")
    print(flavor_text)

    return "成功"



def rest_with_event(character_status, game_state):
    action = "休む"
    location = game_state.get('location', '未知の場所')
    talk_situation = game_state.get('talk_situation', ['normal'])

    flavor_text = generate_flavor_text(action, talk_situation, location)
    print(f"{character_status.name}は休息をとっています……")
    print(flavor_text)

    return "成功"

def engage_combat(character_status, game_state, enemy_character_status=None):
    print(f"{character_status.name}が敵との戦闘を開始します……")

    if enemy_character_status:
        enemy_hp = enemy_character_status.hp
        enemy_attack_power = enemy_character_status.attack_power
        enemy_name = enemy_character_status.name
    else:
        enemy = game_state.get("enemy", {"name": "謎の敵", "hp": 30, "attack_power": 5})
        enemy_hp = enemy["hp"]
        enemy_attack_power = enemy["attack_power"]
        enemy_name = enemy["name"]

    attack_power = character_status.attack_power if character_status.equipped_weapon else 1

    while character_status.hp > 0 and enemy_hp > 0:
        enemy_hp -= attack_power
        print(f"{enemy_name}に{attack_power}のダメージを与えた！ (敵HP: {enemy_hp})")

        if enemy_hp <= 0:
            print(f"{enemy_name}を倒しました！")
            game_state["has_enemy"] = False
            if enemy_character_status:
                enemy_character_status.hp = 0  # 敵のキャラクターを死亡状態にする
            return "勝利"

        character_status.hp -= enemy_attack_power
        print(f"{enemy_name}から{enemy_attack_power}のダメージを受けた！ (HP: {character_status.hp})")

        if character_status.hp <= 0:
            print(f"{character_status.name}は敗北しました……")
            return "敗北"

    # 戦闘後、敵のHPを更新
    if enemy_character_status:
        enemy_character_status.hp = enemy_hp

    return "戦闘終了"

def avoid_combat(character_status, game_state):
    print(f"{character_status.name}は戦闘を避けました。")
    character_status.change_status(hp_change=-5, stamina_change=-10)
    print("体力とスタミナが少し減りました。")
    return "逃走成功"

def accept_attack(character_status, game_state):
    enemy = game_state.get("enemy", {"name": "謎の敵", "attack_power": 5})
    damage = enemy["attack_power"]
    print(f"{character_status.name}は無抵抗で{enemy['name']}の攻撃を受けました！")
    character_status.change_status(hp_change=-damage)
    print(f"{damage}のダメージを受けました。(HP残り：{character_status.hp})")
    return f"{damage}ダメージを受けた"



def perform_attack(character_status, game_state, target="敵"):
    print(f"{character_status.name}が{target}を攻撃しました（仮）")
    # 実装は後ほど！

    # 常に成功するととりあえず仮定
    return "成功"


def talk_to_statue(character_status, game_state):
    """
    古代の石像（オムニ）との対話イベント。
    """
    print(f"{character_status.name}は古代の石像に話しかけた。")
    print("石像が目を開けた……静かに語りかける声が聞こえる。")
    print("『よくぞここまで来た。我が名はオムニ。』")
    print("『この試練を乗り越えし者に、古き知恵を授けよう……』")
    
    # イベントフラグを立てる（例：イベント進行状態を更新）
    game_state["events"] = game_state.get("events", {})
    game_state["events"]["statue_trial_unlocked"] = True
    print("イベント『石像の試練』が解放されました！")


def talk_to_statue_with_cooldown(character_status, game_state):
    current_time = time.time()
    statue_name = game_state.get("current_target", "古代の石像")

    if "cooldown_status" not in game_state:
        game_state["cooldown_status"] = {}
    cooldown_status = game_state["cooldown_status"]

    if cooldown_status.get(statue_name, 0) > current_time:
        remaining_time = cooldown_status[statue_name] - current_time
        print(f"{statue_name}は沈黙しています。あと{int(remaining_time)}秒待つ必要があります。")
        return "クールダウン中（失敗）"

    dialogue = "よくぞここまで来た。我が名はオムニ。この地に訪れし者よ、何を求めてここに来た？"
    print(dialogue)

    # 選択肢を表示
    print("\n選択肢を選んでください:")
    choices = [
        "① 誰よりも強くなりたい",
        "② 自分の生きる意味を知りたい",
        "③ 誰かを助けたい",
        "④ 自由に入力する"
    ]
    for choice in choices:
        print(choice)

    choice = input("\n番号を選択してください（1～4）: ")

    if choice == "1":
        desire = "誰よりも強くなりたい"
    elif choice == "2":
        desire = "自分の生きる意味を知りたい"
    elif choice == "3":
        desire = "誰かを助けたい"
    elif choice == "4":
        desire = input("あなたの願いを自由に入力してください：")
    else:
        print("無効な入力です。")
        return "無効な入力（失敗）"

    # 選択肢①と③の場合は追加の問いかけ
    if choice in ["1", "3"]:
        name = input("オムニ：「ほう。その名は？」名前を入力（空白の場合は「名もなき者」になります）：")
        if not name.strip():
            name = "名もなき者"
    else:
        name = None

    # AIに反応を生成させる
    omni_response = generate_omni_controlled_response(choice, desire, name)

    print(f"\nオムニ：「{omni_response}」")

    cooldown_status[statue_name] = current_time + 10

    return {
        "dialogue": dialogue,
        "player_choice": desire,
        "player_target_name": name,
        "omni_response": omni_response
    }



def generate_card_and_print(character_status, game_state, card_name):
    print(f"新カード「{card_name}」を生成しました。印刷指示を出します。")
    # カード生成と印刷処理のロジック


##オムニの応答とその後の反応

def generate_omni_controlled_response(choice, desire, name=None):
    base_prompt = "あなたは古代の石像「オムニ」です。以下のプレイヤーの願望に対して、哲学的・神秘的な口調で短く回答してください。"

    if choice == "1":
        prompt = f"{base_prompt}\n\nプレイヤーの願望：「{desire}」、その対象の名前：「{name}」"
        response_template = f"強さを求めるか。その道は険しく、{name}の名がどこまで響くかはお前次第だ。"
    elif choice == "2":
        prompt = f"{base_prompt}\n\nプレイヤーの願望：「{desire}」"
        response_template = "生きる意味は己の内に宿る。問い続けることこそがお前の道だ。"
    elif choice == "3":
        prompt = f"{base_prompt}\n\nプレイヤーの願望：「{desire}」、助けたい対象：「{name}」"
        response_template = f"{name}を助ける道は容易くない。覚悟があれば道は開けよう。"
    else:  # 自由入力時
        prompt = f"{base_prompt}\n\nプレイヤーの自由な願望：「{desire}」"
        response_template = None  # AI自由生成に任せる

    # 自由入力の場合のみAIが自由生成。それ以外は制御されたテンプレート
    if response_template:
        return response_template
    else:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": base_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

def determine_next_location(game_state):
    choice = game_state.get("player_choice")

    locations_by_choice = {
        "誰よりも強くなりたい": ["試練の闘技場", "力の洞窟"],
        "自分の生きる意味を知りたい": ["賢者の塔", "運命の泉"],
        "誰かを助けたい": ["囚われの者の遺跡", "救済の森"]
    }

    if choice in locations_by_choice:
        next_locations = locations_by_choice[choice]
    else:
        next_locations = ["未知の世界", "放浪者の草原"]

    selected_location = random.choice(next_locations)
    print(f"次に訪れるべき場所は「{selected_location}」です。")

    game_state["location"] = selected_location

def generate_dynamic_event(player_choice, game_state):
    prompt = f"""
    プレイヤーは現在、「{game_state['location']}」という場所にいます。
    プレイヤーの旅の目的は「{player_choice}」です。

    これらの情報を基に、このロケーションで起こりうる短いイベントを生成してください。
    イベントはプレイヤーの目的に関連し、没入感のある短い描写（100文字以内）で提供してください。
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "プレイヤーの目的とロケーションに関連した短いイベントを生成します。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    event_description = response.choices[0].message.content
    print(event_description)

    return event_description

def generate_location_event(location, event_type, player_choice, difficulty):
    prompt = f"""
    プレイヤーは現在「{location}」におり、目的は「{player_choice}」です。
    イベントタイプは「{event_type}」、難易度は「{difficulty}」です。

    上記を踏まえ、プレイヤーにとって没入感があり、プレイヤーの目的に関連した100文字以内の短いイベント描写を生成してください。
    描写は具体的で、場所とイベントタイプに矛盾しないようにしてください。
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "場所、イベントタイプ、難易度、プレイヤーの目的を元にした汎用的イベント描写を生成します。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    event_description = response.choices[0].message.content
    return event_description

def choose_event_parameters():
    event_types = ["戦闘", "探索", "会話", "謎解き"]
    difficulties = ["Easy", "Normal", "Hard"]

    selected_event_type = random.choice(event_types)
    selected_difficulty = random.choices(difficulties, weights=[0.4, 0.4, 0.2])[0]

    return selected_event_type, selected_difficulty

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

def npc_speak(npc_name, dialogue_key):
    dialogue = fixed_dialogue.get(npc_name, {}).get(dialogue_key, "")
    if dialogue:
        print(f"{npc_name}：「{dialogue}」")
    else:
        print(f"{npc_name}は何も言わなかった。")

    return dialogue  # ログ記録のため返す

# NPCがセリフを発した後、ログ記録
def npc_speak_and_log(npc_name, dialogue_key, location, game_state):
    dialogue = npc_speak(npc_name, dialogue_key)
    
    # ログに記録
    log_action(
        actor=npc_name,
        action=f"セリフ：{dialogue_key}",
        target=None,
        location=location,
        result=dialogue,
        game_state=game_state
    )


