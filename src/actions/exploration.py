from .utility import generate_flavor_text  # この行を追加する
from .combat import engage_combat  # この行を追加する
import random
#openaiインポートセット
import openai
import os
from dotenv import load_dotenv
# .envから環境変数を読み込む
load_dotenv()

# .env内にあるAPIキーを使う
openai.api_key = os.getenv("OPENAI_API_KEY")
import random

def explore_location(character_status, game_state):
    location = game_state.get('location', '未知の場所')
    has_enemy = game_state.get('has_enemy', False)

    print(f"{character_status.name}が{location}を探索しています……")

    if has_enemy:
        encounter_chance = random.random()
        if encounter_chance < 0.5:  # 50%の確率で敵に気付かれる
            print("探索中に敵に気付かれた！戦闘が始まる！")
            engage_combat(character_status, game_state)
            return "敵に襲われ戦闘開始"
        else:
            # 敵に気付かれず探索成功
            print("敵に気付かれず、慎重に探索した……")
            # 解決策やアイテムが見つかる可能性を追加
            if random.random() < 0.5:  # さらに50%の確率でヒントを発見
                print("探索中に有利なヒントを見つけた！")
                # ゲームステートにヒントを追加
                game_state["hint"] = "敵の弱点が判明した！攻撃力が一時的に上昇する。"
                return "探索成功（ヒント発見）"
            else:
                print("特に役立つものは見つからなかった……")
                return "探索成功（収穫なし）"
    else:
        print("安全に探索を完了した。")
        # 通常の探索報酬やフレーバーテキスト
        flavor_text = generate_flavor_text("探索", ["normal"], location)
        print(flavor_text)
        return "探索成功（安全）"




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