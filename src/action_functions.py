import time
from logger import log_action  # ログ関数をインポートする例

# クールダウン管理の状態保持（グローバル変数かクラス内の属性が理想）
cooldown_status = {}

def move_forward(character_status, game_state):
    print(f"{character_status.name}が奥に進みました。")
    # その他の具体的なロジックをここに書く

    # 常に成功すると仮定
    return "成功"

def rest_with_event(character_status, game_state):
    print(f"{character_status.name}は休んでいます（仮）")
    # 実装は後ほど！

    # 常に成功すると仮定
    return "成功"

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
        return "クールダウン中（失敗）"  # 戻り値で結果を返すだけ（ログは書かない）

    print(f"{character_status.name}は{statue_name}に話しかけました。")
    cooldown_status[statue_name] = current_time + 10
    return "成功"  # 成功時の戻り値を返す（ログは書かない）

def generate_card_and_print(character_status, game_state, card_name):
    print(f"新カード「{card_name}」を生成しました。印刷指示を出します。")
    # カード生成と印刷処理のロジック
