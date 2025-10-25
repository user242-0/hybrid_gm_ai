# scripts/sg_to_prompt.py  — robust stringify for camera/lighting/TPO
from __future__ import annotations
from pathlib import Path
import argparse, json, yaml

_LOC_MAP = {"洞窟":"cave interior","フィールド":"open field","祭壇":"stone altar","廊下":"stone corridor"}
_TIME_MAP= {"night":"at night, low-key lighting",
            "dusk":"at sunset, golden hour, long shadows",
            "day":"daylight, neutral color",
            "morning":"soft morning light"}

def _to_text(x) -> str:
    """Any → str。dictは text優先、無ければ k: v を畳み込み。list/tuple は再帰連結。"""
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip()
    if isinstance(x, (list, tuple, set)):
        parts = [_to_text(e) for e in x]
        return ", ".join([p for p in parts if p])
    if isinstance(x, dict):
        # camera/lighting 用に 'text' を優先
        if isinstance(x.get("text"), str) and x["text"].strip():
            return x["text"].strip()
        kv=[]
        for k, v in x.items():
            sv = _to_text(v)
            if not sv:
                continue
            # なるべく読みやすく
            if isinstance(v, (int, float)) or len(sv.split()) <= 2:
                kv.append(f"{k} {sv}")
            else:
                kv.append(f"{k}: {sv}")
        return ", ".join(kv)
    return str(x)

def sg_to_prompt(sg: dict, *, style: str = "realistic") -> tuple[str, str, dict]:
    theme = _to_text(sg.get("theme",""))
    bg    = _to_text(sg.get("background",""))

    meta  = sg.get("meta",{}) or {}
    tpo   = meta.get("tpo_ctx",{}) or {}
    cam   = _to_text(meta.get("camera"))
    light = _to_text(meta.get("lighting"))

    loc_tok  = _to_text(_LOC_MAP.get(str(tpo.get("location","")), ""))
    time_tok = _to_text(_TIME_MAP.get(str(tpo.get("time","")), ""))

    parts = [p for p in [loc_tok, time_tok, theme, bg, cam, light] if p]

    # objects の要約（簡易）
    for o in sg.get("objects") or []:
        seg = [
            _to_text(o.get("name","")),
            _to_text(o.get("action","")),
            _to_text((o.get("pose") or {}).get("text","")),
            _to_text(o.get("materials_hint","")),
        ]
        seg = [s for s in seg if s]
        if seg:
            parts.append(", ".join(seg))

    style_hint = {
        "realistic":"highly detailed, physically-based rendering, cinematic lighting, depth of field",
        "anime":"anime style, clean lineart, cel shading, vibrant colors",
        "sketch":"pencil sketch, rough shading, dynamic composition"
    }.get(style,"")
    prompt = ", ".join(parts + ([style_hint] if style_hint else []))
    negative = "low quality, blurry, extra limbs, deformed hands, text artifacts"

    # メタはそのまま残しつつ、文字列化したテキストも保存
    out_meta = {
        "style": style,
        "tpo_ctx": tpo,
        "camera": meta.get("camera"),
        "lighting": meta.get("lighting"),
        "camera_text": cam,
        "lighting_text": light,
    }
    seed = int(((sg.get("outputs") or {}).get("image") or {}).get("seed", 0))
    out_meta["seed"] = seed
    return prompt, negative, out_meta

def process_job(job_dir: Path, *, style: str):
    sg_p = job_dir / "scene_graph.yml"
    if not sg_p.exists():
        print("skip (no SG):", job_dir); return
    sg = yaml.safe_load(sg_p.read_text(encoding="utf-8")) or {}
    prompt, negative, meta = sg_to_prompt(sg, style=style)
    out = job_dir / "render"; out.mkdir(parents=True, exist_ok=True)
    (out/"prompt.txt" ).write_text(prompt,   encoding="utf-8")
    (out/"negative.txt").write_text(negative,encoding="utf-8")
    (out/"meta.json"   ).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote:", out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--jobs", nargs="+", required=True)
    ap.add_argument("--style", default="realistic", choices=["realistic","anime","sketch"])
    args=ap.parse_args()
    import glob
    hits=[]
    for pat in args.jobs: hits += [Path(p) for p in glob.glob(pat)]
    for h in sorted(set(hits)):
        if h.is_file(): h=h.parent
        if h.is_dir(): process_job(h, style=args.style)

if __name__=="__main__":
    main()
