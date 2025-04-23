import time
from logger import log_action  # ログ関数をインポートする例
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
fixed_dialogue = {
"石像に話す": "よくぞここまで来た。我が名はオムニ。この地に訪れし者よ、何を求めてここに来た？"
}

fixed_dialogue_2 = {
"オムニ：「今は語るべきことがない。時を置いて訪れよ。」"
}

# フレーバーテキスト生成関数
# 簡単なキャッシュ
flavor_text_cache = {}

def generate_flavor_text(talk_situation, location):
    time_description = "深夜（夜間・真夜中）" if "late_night" in talk_situation else "昼間（通常時間帯）"
    
    # 「朝」「昼」など深夜に不適切な言葉を禁止
    prompt = f"""
    あなたはゲーム内の短めのフレーバーテキストを生成するAIです。

    場所：{location}（例：祭壇、洞窟など）
    時間帯：{time_description}
    状況：「{', '.join(talk_situation)}」（例：深夜、短時間の連続会話など）

    深夜の描写の場合、「朝」「昼」「陽光」「小鳥のさえずり」など、夜間には存在しない要素は絶対に含めず、月光や暗闇など、夜にふさわしい要素のみを使用してください。
    100文字以内の簡潔で矛盾のない描写を生成してください。
    セリフやストーリー要素は一切含めないでください。
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたは指定された場所・時間帯・状況に矛盾のない短い情景描写を生成するAIです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content



##　実際のアクションリスト

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

    
    talk_situation = game_state.get('talk_situation', [])
    talk_count = game_state.get('talk_count')
    interval = game_state.get('interval')

    # print(f"[デバッグ] talk_count: {talk_count}, interval: {interval}")
    if talk_count is not None and talk_count >= 3 and interval is not None and interval < 60:
        print(fixed_dialogue_2)
        return "時間をかけて再訪することをプレイヤーに促す"


    print(f"{character_status.name}は{statue_name}に話しかけました。")

    
    dialogue = fixed_dialogue["石像に話す"] #セリフの中身
    talk_situation = game_state.get('talk_situation', 'normal')
    flavor_text = generate_flavor_text(talk_situation,  game_state.get('location', '祭壇'))


    # 正しく表示
    print(dialogue)
    print(flavor_text)

    cooldown_status[statue_name] = current_time + 10

    # 必要であれば返り値に含めてログ記録も可能
    return {"dialogue": dialogue, "flavor_text": flavor_text}

def generate_card_and_print(character_status, game_state, card_name):
    print(f"新カード「{card_name}」を生成しました。印刷指示を出します。")
    # カード生成と印刷処理のロジック
