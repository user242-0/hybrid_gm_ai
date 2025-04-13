

def move_forward(character_status, game_state):
    print(f"{character_status.name}が奥に進みました。")
    # その他の具体的なロジックをここに書く

def rest_with_event(character_status, game_state):
    print(f"{character_status.name}は休んでいます（仮）")
    # 実装は後ほど！

def perform_attack(character_status, game_state, target="敵"):
    print(f"{character_status.name}が{target}を攻撃しました（仮）")
    # 実装は後ほど！

def generate_card_and_print(character_status, game_state, card_name):
    print(f"新カード「{card_name}」を生成しました。印刷指示を出します。")
    # カード生成と印刷処理のロジック
