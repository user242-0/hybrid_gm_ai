from .utility import generate_flavor_text  # この行を追加する
from .combat import engage_combat  # この行を追加する
import random
#openaiインポートセット
# import openai
import sys
import os
_OPENAI = None
from dotenv import load_dotenv
# .envから環境変数を読み込む
load_dotenv()

import random
###
def _use_stub_llm():
    return os.getenv("GM_USE_STUB") == "1" or os.getenv("CI") == "true"


def _get_client():
    """OpenAIクライアントを遅延初回だけ作成。2回目以降はキャッシュ。"""
    global _CLIENT
    if _CLIENT is None:
        from openai import OpenAI        # ← 遅延importなのでテストでは呼ばれない
        # APIキーは環境変数 OPENAI_API_KEY を自動利用。手動指定も可:
        _CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _CLIENT

def normalize_location_keys(gs: dict):
    # 古いコードが gs["location"] を使っていても落ちないようにする
    if "current_location" not in gs and "location" in gs:
        gs["current_location"] = gs["location"]

# 例：simulation_e.py の該当箇所付近に置く
def _coerce_action_text(action):
    if isinstance(action, dict):
        return action.get("label") or action.get("name") or action.get("description") or str(action)
    return getattr(action, "name", str(action))

def _coerce_talk_situation(ts):
    if ts is None:
        return {"why_now": "player_choice", "salience": 0.3}
    if isinstance(ts, dict):
        return {"why_now": ts.get("why_now", "player_choice"),
                "salience": float(ts.get("salience", 0.3))}
    # dataclass / obj でも吸収
    try:
        d = vars(ts)
        return {"why_now": d.get("why_now", "player_choice"),
                "salience": float(d.get("salience", 0.3))}
    except Exception:
        return {"why_now": "player_choice", "salience": 0.3}

def _coerce_location(loc, game_state):
    name = (getattr(loc, "name", None) or (loc if isinstance(loc, str) else None)
            or game_state.get("current_location") or "どこか")
    return name

def safe_generate_flavor_text(action, talk_situation, location, game_state, director=None, logger=print):
    # Directorの判定（無ければ許可。None/未定義は許可に倒す）
    if director and hasattr(director, "should_emit_flavor_text"):
        try:
            if director.should_emit_flavor_text({"action": action, "talk_situation": talk_situation,
                                                 "location": location, "game_state": game_state}) is False:
                return ""  # 抑制
        except Exception as e:
            logger(f"[Director warn] should_emit_flavor_text error: {e}")

    a = _coerce_action_text(action)
    ts = _coerce_talk_situation(talk_situation)
    loc = _coerce_location(location, game_state)

    try:
        text = generate_flavor_text(a, ts, loc)
        if not text or not str(text).strip():
            logger("[Flavor warn] empty text; using fallback")
            return f"{a}。{loc}の空気がわずかに揺れた。"
        
        return text 
    except Exception as e:
        logger(f"[Flavor ERROR] {e}")
        return f"{a}。{loc}で静かに時が過ぎる…"

# 呼び出し側はこれに置換
# flavor_text = safe_generate_flavor_text(action, talk_situation, location, game_state, director, logger)

ACTION_CANON = {
    "進む": "move", "移動する": "move", "go": "move", "move": "move",
    # 必要に応じて増やす
}
"""
def generate_flavor_text(action, talk_situation, location):
    print(f"[flavor-in] action={action!r}, ts={talk_situation}, loc={location!r}")
    key = ACTION_CANON.get(action, action)  # ラベル→キー正規化
    loc = location or "未知の場所"
    sal = float(getattr(talk_situation, "salience", 0.3) 
                if not isinstance(talk_situation, dict) 
                else talk_situation.get("salience", 0.3))

    # ここから分岐
    if key == "move":
        base = f"{action}。{loc}の空気がかすかに揺れる。"
        # 抑制しても“空”にはしない
        if sal < 0.15:
            return base
        return f"{action}。{loc}へ一歩踏み出すと、足裏に新しい感触が伝わった。"
    # ...他のアクション...
    # 最後の砦（絶対に空を返さない）
    return f"{action}。{loc}の空気がかすかに揺れる。"
"""
def explore_location(character_status, game_state):
    location = game_state.get('current_location', '未知の場所')
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




def _advance_position(game_state, direction=None):
    """world.advance が無い環境でも絶対に次の pos/loc を返すフォールバック"""
    world = game_state.get("world")
    pos   = game_state.get("position")

    # 1) world オブジェクトがあれば優先
    if world and hasattr(world, "advance"):
        try:
            return world.advance(pos, direction)
        except Exception as e:
            print(f"[move warn] world.advance failed: {e}")

    # 2) フォールバック：position を素朴に前進させる
    if isinstance(pos, dict) and "x" in pos and "y" in pos:
        # 2D グリッドを想定（前進＝+y）
        new_pos = {**pos, "y": pos["y"] + 1}
        new_loc = f"通路({new_pos['x']},{new_pos['y']})"
    elif isinstance(pos, (tuple, list)) and len(pos) >= 2:
        new_pos = (pos[0], pos[1] + 1, *pos[2:])
        new_loc = f"通路({new_pos[0]},{new_pos[1]})"
    else:
        # ステップ番号として扱う
        step = int(pos or 0) + 1
        new_pos = step
        new_loc = f"通路{step}"

    return new_pos, new_loc


def move_forward(character_status, game_state, *args):
    normalize_location_keys(game_state)
    action = "進む"

    # ※ direction は任意：game_state にあれば利用、無ければ None のまま
    direction = game_state.get("direction")

    # 1) 位置を進める（world が無くてもフォールバックで進む）
    new_pos, new_loc = _advance_position(game_state, direction)
    game_state["position"] = new_pos

    # 2) 表示用の場所名を確定し、current_location を更新
    loc_name = (getattr(new_loc, "name", None) or str(new_loc) or "入口")
    game_state["current_location"] = loc_name

    # 3) フレーバー生成（必ず一文は返る設計）
    talk_situation = {"why_now": "player_choice", "salience": 0.3}
    flavor_text = safe_generate_flavor_text(action, talk_situation, loc_name, game_state, None, print)
    if not flavor_text.strip():
        flavor_text = f"{action}。{loc_name}の空気がわずかに揺れた。"

    print(f"{character_status.name}は進みます……")
    print(flavor_text)
    return "成功"



def rest_with_event(character_status, game_state):
    action = "休む"
    location = game_state.get('current_location', '未知の場所')
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
    if _use_stub_llm():
        return f"空気がわずかに揺れた。"
    client = _get_client() 
    prompt = f"""
    プレイヤーは現在、「{game_state['location']}」という場所にいます。
    プレイヤーの旅の目的は「{player_choice}」です。

    これらの情報を基に、このロケーションで起こりうる短いイベントを生成してください。
    イベントはプレイヤーの目的に関連し、没入感のある短い描写（100文字以内）で提供してください。
    """

    response = client.chat.completions.create(
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
    if _use_stub_llm():
        return f"空気がわずかに揺れた。"
    client = _get_client()     
    prompt = f"""
    プレイヤーは現在「{location}」におり、目的は「{player_choice}」です。
    イベントタイプは「{event_type}」、難易度は「{difficulty}」です。

    上記を踏まえ、プレイヤーにとって没入感があり、プレイヤーの目的に関連した100文字以内の短いイベント描写を生成してください。
    描写は具体的で、場所とイベントタイプに矛盾しないようにしてください。
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "場所、イベントタイプ、難易度、プレイヤーの目的を元にした汎用的イベント描写を生成します。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    event_description = response.choices[0].message.content
    return event_description

