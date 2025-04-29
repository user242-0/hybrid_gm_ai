import random 
#openaiインポートセット
import openai
import os
from dotenv import load_dotenv
# .envから環境変数を読み込む
load_dotenv()

# .env内にあるAPIキーを使う
openai.api_key = os.getenv("OPENAI_API_KEY")

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

def generate_card_and_print(character_status, game_state, card_name):
    print(f"新カード「{card_name}」を生成しました。印刷指示を出します。")
    # カード生成と印刷処理のロジック

def choose_event_parameters():
    event_types = ["戦闘", "探索", "会話", "謎解き"]
    difficulties = ["Easy", "Normal", "Hard"]

    selected_event_type = random.choice(event_types)
    selected_difficulty = random.choices(difficulties, weights=[0.4, 0.4, 0.2])[0]

    return selected_event_type, selected_difficulty
