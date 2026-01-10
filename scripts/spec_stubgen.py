#!/usr/bin/env python3
import argparse
import re
import sys
import types
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import yaml

if "dotenv" not in sys.modules:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *args, **kwargs: False
    sys.modules["dotenv"] = dotenv_stub

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from src.action_definitions import get_action_specs

CONDITION_VAR_RE = re.compile(r"\s*([A-Za-z_][\w\.]*)\s*(?:[<>]=|<|>|==)")
DONE_EFFECT_RE = re.compile(r"^\s*([A-Za-z_][\w\.]*)\s*(>=|<=)\s*(\d+)\s*$")


def iter_pack_files(packs_dir: Path) -> Iterable[Path]:
    for path in sorted(packs_dir.glob("*.yml")):
        if path.is_file():
            yield path


def load_pack(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def dump_yaml_text(data: Dict[str, Any]) -> str:
    rendered = yaml.safe_dump(data, allow_unicode=True)
    if isinstance(rendered, tuple):
        rendered = rendered[0]
    if not isinstance(rendered, str):
        rendered = str(rendered)
    return rendered


def dump_pack(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(dump_yaml_text(data))


def extract_condition_vars(text: str) -> Optional[str]:
    match = CONDITION_VAR_RE.match(text)
    if not match:
        return None
    return match.group(1)


def extract_done_effect(done: str, action_id: str) -> Dict[str, Any]:
    match = DONE_EFFECT_RE.match(done)
    if match:
        var = match.group(1)
        op = match.group(2)
        if op == ">=":
            return {"op": "add", "path": var, "value": 1}
        return {"op": "add", "path": var, "value": -1, "min": 0}
    return {"op": "add", "path": f"stub.{action_id}", "value": 1}


def merge_action_meta(meta: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in update.items():
        if value is None:
            continue
        if key not in meta or meta[key] in (None, ""):
            meta[key] = value
    return meta


def collect_pack_data(pack: Dict[str, Any]) -> Tuple[Set[str], Dict[str, Dict[str, Any]], Set[str], Set[str]]:
    action_ids: Set[str] = set()
    action_meta: Dict[str, Dict[str, Any]] = {}
    condition_vars: Set[str] = set()
    effect_paths: Set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            action_id = node.get("action") or node.get("action_id")
            if isinstance(action_id, str):
                action_ids.add(action_id)
                meta = action_meta.get(action_id, {})
                update = {
                    "text": node.get("text"),
                    "time_min": node.get("time_min"),
                    "done": node.get("done"),
                }
                action_meta[action_id] = merge_action_meta(meta, update)
            for key, value in node.items():
                if key in {"condition", "done"} and isinstance(value, str):
                    var = extract_condition_vars(value)
                    if var:
                        condition_vars.add(var)
                if key == "effects" and isinstance(value, list):
                    for effect in value:
                        if isinstance(effect, dict):
                            path = effect.get("path")
                            if isinstance(path, str) and path:
                                effect_paths.add(path)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(pack)
    return action_ids, action_meta, condition_vars, effect_paths


def ensure_action_dict(pack: Dict[str, Any]) -> Dict[str, Any]:
    actions_data = pack.get("actions")
    if actions_data is None:
        pack["actions"] = {}
        return pack["actions"]
    if isinstance(actions_data, dict):
        return actions_data
    if isinstance(actions_data, list):
        converted: Dict[str, Any] = {}
        for item in actions_data:
            if isinstance(item, dict) and item.get("id"):
                converted[item["id"]] = item
        pack["actions"] = converted
        return converted
    pack["actions"] = {}
    return pack["actions"]


def set_default_path(target: Dict[str, Any], path: str, value: Any = 0) -> None:
    keys = path.split(".")
    current: Dict[str, Any] = target
    for key in keys[:-1]:
        existing = current.get(key)
        if existing is None:
            current[key] = {}
            current = current[key]
        elif isinstance(existing, dict):
            current = existing
        else:
            return
    leaf = keys[-1]
    if leaf not in current:
        current[leaf] = value


def seed_world_defaults(
    pack: Dict[str, Any],
    condition_vars: Set[str],
    effect_paths: Set[str],
) -> bool:
    if not condition_vars and not effect_paths:
        return False
    world_defaults = pack.get("world_defaults")
    if world_defaults is None:
        world_defaults = {}
        pack["world_defaults"] = world_defaults
    if not isinstance(world_defaults, dict):
        return False
    before = dump_yaml_text(world_defaults)
    for var in sorted(condition_vars | effect_paths):
        set_default_path(world_defaults, var, 0)
    after = dump_yaml_text(world_defaults)
    return before != after


def build_stub(action_id: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    label = meta.get("text") or action_id
    time_min = meta.get("time_min")
    done = meta.get("done") or ""
    effects = [extract_done_effect(str(done), action_id)]
    return {
        "label": label,
        "description": f"AUTO-STUB: {label}",
        "time_min": int(time_min or 0),
        "emotion_delta": None,
        "effects": effects,
        "tags": ["auto_stub"],
        "requirements": None,
        "args_template": [],
        "available_to": ["player", "npc"],
    }


def summarize_missing(pack_path: Path, missing: List[str]) -> None:
    print(f"{pack_path.name}: missing={len(missing)}")
    if missing:
        for action_id in missing:
            print(f"  - {action_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate stub ActionSpecs for packs.")
    parser.add_argument("--packs", type=Path, default=Path("data/director/packs"))
    parser.add_argument("--write", action="store_true", help="Write stubs into pack YAML files.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List missing action specs without writing files.",
    )
    args = parser.parse_args()

    packs_dir = args.packs
    if not packs_dir.exists():
        raise SystemExit(f"Packs directory not found: {packs_dir}")

    wrote_files: List[Path] = []
    for pack_path in iter_pack_files(packs_dir):
        pack = load_pack(pack_path)
        action_ids, action_meta, condition_vars, effect_paths = collect_pack_data(pack)
        specs = get_action_specs(pack)
        missing = sorted(action_ids - set(specs.keys()))
        summarize_missing(pack_path, missing)

        if args.write:
            changed = False
            actions_dict = ensure_action_dict(pack)
            for action_id in missing:
                if action_id in actions_dict:
                    continue
                meta = action_meta.get(action_id, {})
                actions_dict[action_id] = build_stub(action_id, meta)
                effect_paths.add(actions_dict[action_id]["effects"][0]["path"])
                changed = True
            if seed_world_defaults(pack, condition_vars, effect_paths):
                changed = True
            if changed:
                dump_pack(pack_path, pack)
                wrote_files.append(pack_path)

    if args.write:
        if wrote_files:
            print("\nUpdated pack files:")
            for path in wrote_files:
                print(f"  - {path}")
        else:
            print("\nNo pack files updated.")
    elif args.dry_run or not args.write:
        print("\nDry-run complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
