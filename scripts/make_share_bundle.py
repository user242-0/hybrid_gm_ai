# scripts/make_share_bundle.py
from __future__ import annotations
import yaml, zipfile
from pathlib import Path

MANIFEST = Path("chatgpt_shared_manifest.yml")
OUT = Path("share_bundle.zip")

def iter_paths(manifest: dict):
    groups = ["must_share", "recommended"]  # 必要なら nice_to_have も
    for g in groups:
        for pat in manifest.get(g, []) or []:
            for p in Path(".").glob(pat):
                if p.is_file():
                    yield p

def main():
    y = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    files = sorted(set(iter_paths(y)))
    print(f"bundle candidates: {len(files)} files")
    if len(files) > 40:
        print("! warn: exceeds 40. trim manifest or move some to nice_to_have.")
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f.as_posix())
            print(" +", f)
    print("wrote:", OUT)

if __name__ == "__main__":
    main()
# python scripts/make_share_bundle.py
# -> share_bundle.zip（must_share + recommended だけが入る）