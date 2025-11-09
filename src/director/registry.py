from __future__ import annotations

from typing import Dict, Tuple
import re
import yaml
import pathlib

PACK_DIR = pathlib.Path("data/director/packs")

RULES = [
    (r"(刑事|cop|愉快犯|trickster)", "cop_trickster"),
    (r"(従者|主従|風来坊|retainer|drifter)", "rogue_master"),
    (r"(マトリックス|仮想現実|simulation|覚醒|glitch)", "pseudo_matrix"),
]


def select_pack_id(premise_text: str) -> str:
    t = premise_text.lower()
    for pat, pid in RULES:
        if re.search(pat, premise_text) or re.search(pat, t):
            return pid
    return "cop_trickster"


def load_pack(pack_id: str) -> Dict:
    with open(PACK_DIR / f"{pack_id}.yml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def synthesize_from_text(premise_text: str) -> Tuple[Dict, Dict, str]:
    pid = select_pack_id(premise_text)
    data = load_pack(pid)
    premise = {
        "title": data.get("title", pid),
        "seed": data.get("seed", 41),
        "roles": data.get("roles", {}),
        "modes_enabled": data.get("modes_enabled", []),
        "tone": data.get("tone", []),
    }
    goals = {"modes": data["modes"]}
    return premise, goals, pid
