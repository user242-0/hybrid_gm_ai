

def move_forward(character_status, game_state):
    print(f"{character_status.name}が奥に進みました。")
    # その他の具体的なロジックをここに書く

def rest_with_event(character_status, game_state):
    print(f"{character_status.name}は休んでいます（仮）")
    # 実装は後ほど！

def perform_attack(character_status, game_state, target="敵"):
    print(f"{character_status.name}が{target}を攻撃しました（仮）")
    # 実装は後ほど！

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


def generate_card_and_print(character_status, game_state, card_name):
    print(f"新カード「{card_name}」を生成しました。印刷指示を出します。")
    # カード生成と印刷処理のロジック
