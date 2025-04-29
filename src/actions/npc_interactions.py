import time
from logger import log_action


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
