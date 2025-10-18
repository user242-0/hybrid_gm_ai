# simulation_utils.py （場所は任意）
import json
from src.event_bus import log_q   # ※使わないなら削除可

from src.choice_definitions   import choice_definitions
from src.action_definitions   import actions
from src.requirements_checker import RequirementsChecker
from src.utility.args_parser    import parse_args            # 既にある util を想定
from src.logger               import log_action
#register用import
from src.character_status import CharacterStatus
# --- 不要な import を削除 ---
# from src.simulation_e import rc_tick
# from src.scheduler import Scheduler

#以下、datalab用インポート
import re
from pathlib import Path
from datalab.registry.action_registry import normalize_action
from datalab.registry.scene_resolver import resolve
from datalab.emitters.scene_graph_emitter import emit_scene_graph
from schemas.scene_graph import ObjectSpec, Pose

from datalab.emitters.story_emitter import emit_story_line
from datalab.emitters.emotion_emitter import emit_emotion_eval, summarize_why_now
from utility.config_loader import get_cfg, job_root_from_cfg

CFG = get_cfg()
SCENE_EMIT_ON = bool(CFG["datalab"].get("emit_scene_graph", True))
SCENE_JOB_DIR = job_root_from_cfg()

def _guess_materials_from_player(player, action: str):
    mats = []
    w = getattr(player, "equipped_weapon", None)
    wtype = w.get("weapon_type") if isinstance(w, dict) else getattr(w, "weapon_type", None)
    if action in ("swing_sword", "attack") and wtype == "sword":
        mats += ["steel_brushed", "leather_soft"]
    return mats

def _build_ctx(player, game_state, action: str, args: list[str], raw_key: str | None = None):
    # 関係ラベルの取得（ターゲット名は args 先頭 or game_state 既定）
    target_name = (args[0] if args else game_state.get("current_target"))
    labels = set()
    tgt = None
    if target_name and hasattr(player, "get_labels_from"):
        # game_state.party から対象を引けるユーティリティがあるなら使う
        party = game_state.get("party", {})
        tgt = party.get(target_name)
        if tgt and hasattr(tgt, "relationship_tags_from"):
            labels = tgt.relationship_tags_from.get(player.name, set())

    r, g, b = getattr(player, "emotion_color", (127,127,255))

    return {
        "actor": player.name,
        "raw_key": (raw_key if raw_key is not None else action), 
        "action": action,                # 正規化後
        "args": args,
        "location": game_state.get("current_location", "どこか"),
        "time": game_state.get("time_of_day", "night"),
        "relation_labels": labels,
        "emotion": {"red": r/255.0, "green": g/255.0, "blue": b/255.0},
    }

# emit_from_choice の定義を少し拡張（why_now, profile, actor情報を渡す）
def emit_from_choice(player, key: str, args: list[str], game_state, why_now: str | None = None):
    if not CFG["datalab"].get("emit_scene_graph", True):
        return
    action = normalize_action(key, args)
    ctx = _build_ctx(player, game_state, action, args, raw_key=key)
    picked = resolve(ctx)  # scene_policy.yaml を解決

    # objects は YAML から来る dict 群を ObjectSpec/Pose に変換
    objs = []
    for o in (picked.get("objects") or []):
        pose = o.get("pose")
        pose_obj = Pose(**pose) if isinstance(pose, dict) else None

        # ここで kwargs を組み立て、None の項目は渡さない
        kwargs = dict(
            name=o.get("name", "{actor}").format(actor=player.name),
            category=o.get("category", "character"),
            base_prompt=o.get("base_prompt", ""),
            action=o.get("action", action),
            pose=pose_obj,
        )

        # materials_hint は list を要求 → 文字列なら [str] に、None は渡さない
        mats = o.get("materials_hint", None)
        if mats is not None:
            if isinstance(mats, (list, tuple, set)):
                kwargs["materials_hint"] = list(mats)
            else:
                kwargs["materials_hint"] = [mats]  # YAMLで単一文字列の場合に対応

        # scale は dict を要求 → dict のときだけ渡す（None や不正型は渡さない）
        sc = o.get("scale", None)
        if isinstance(sc, dict):
            kwargs["scale"] = sc

        objs.append(ObjectSpec(**kwargs))
    fallback_mats = _guess_materials_from_player(player, action)
    fallback_kwargs = dict(
        name=f"{player.name}",
        category="character",
        base_prompt="default character",
        action=action,
    )
    if fallback_mats:
        fallback_kwargs["materials_hint"] = fallback_mats

    objects=objs if objs else [ObjectSpec(**fallback_kwargs)]
    print("[CTX]", ctx["location"], ctx["time"], ctx["raw_key"], "=>", ctx["action"])
    print("[PICKED-keys]", list(picked.keys()))

    emit_scene_graph(
        job_root=SCENE_JOB_DIR,
        theme=picked.get("theme", f"{ctx['location']}での{action}"),
        background=picked.get("background", "generic scene"),
        objects=objects,
        loras=picked.get("loras", []),
        why_now=why_now,
        profile=CFG.get("profile", "prod"),
        actor=player.name, action=action, args=args,
        extra_meta={"camera": picked.get("camera"), "lighting": picked.get("lighting"),
                    "tpo_ctx": {"location": ctx["location"], "time": ctx["time"],
                                "relation_labels": sorted(list(ctx["relation_labels"]))}},
    )


def execute_player_choice(player, cmd: str, game_state):
    """
    cmd は GUI で入力した文字列（例: 'attack' / '1' / 'switch Hero'）
    1) Choice を特定し requirements をチェック
    2) 対応する action.function を呼び出す
    3) ログを残す（persist   + 画面用 log_q）
    """
    # ---- (1) 入力文字列を Choice にマッピング ----
    #   例: 数字なら choice_definitions のインデックス順で解釈 など
    # 入力を解析
    if cmd.isdigit():
        idx = int(cmd) - 1
        keys = list(choice_definitions.keys())
        if idx < 0 or idx >= len(keys):
            game_state["last_action_note"] = {"text": f"⚠ 無効な番号: {cmd}", "tag": "red"}
            return
        key = keys[idx]
        rest = []
    else:
        parts = cmd.split()
        key  = parts[0] if parts else ""
        rest = parts[1:] if len(parts) > 1 else []

    if key not in choice_definitions:
        game_state["last_action_note"] = {"text": f"⚠ 無効なコマンド: {cmd}", "tag": "red"}
        return

    choice_meta = choice_definitions[key]
    action_info = actions[key]
    checker = RequirementsChecker(game_state, player)
    if not checker.check_all(action_info.get("requirements")):
        game_state["last_action_note"] = {"text": f"⚠ 実行条件を満たしていません: {key}", "tag": "red"}
        return

    # まずGUIで自動解決できる引数は埋める
    args = list(rest)
    if not args:
        if key == "攻撃する":
            enemy = game_state.get("enemy")
            if enemy:
                args = [enemy.name]
            elif game_state.get("current_target"):
                # 例：初期状態だと「古代の石像」を攻撃対象にする
                args = [game_state["current_target"]]
    # まだ空なら汎用パーサに委譲（※ 文字列ではなく CharacterStatus を渡す）
    if not args:
        args = parse_args(action_info, player, game_state)

    result = action_info["function"](player, game_state, *args)


    # ---- (3) ログ出力 ----
    # 3-a) 永続ログ
    log_action(
        actor      = player.name,
        action_key = key,
        target     = " ".join(args) if args else "",
        result     = result,
        #game_state = game_state,
    )
    # 3-b) 画面ノート（次の手番で α として出す）
    line = f"[PLY] {player.name} ▶ {key} {' '.join(args)}"
    game_state["last_action_note"] = {
        "text": line,
        "tag":  "green"
    }


    signals_doc = emit_emotion_eval(SCENE_JOB_DIR, actor_obj=player, game_state=game_state)
    thresholds  = CFG["datalab"].get("emit_thresholds", {})
    decision    = summarize_why_now(signals_doc.get("signals", {}), thresholds)

    policy = CFG["datalab"].get("emit_policy", "always")
    emit_ok = (policy == "always") or (policy == "threshold" and decision["ok"])
    why_now_text = f'{decision["text"]} | policy={policy} {"emit" if emit_ok else "skip"}'

    if emit_ok:
        emit_from_choice(player, key, args, game_state, why_now=why_now_text)
    # （この後に story_emitter 等を呼ぶ）

    # 追加：可読ログ（Story）
    emit_story_line(SCENE_JOB_DIR, actor=player.name, action=key, args=args, game_state=game_state)
    
    return result       # ← 戻り値として返すだけ
