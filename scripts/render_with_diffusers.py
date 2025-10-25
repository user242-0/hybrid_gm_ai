# scripts/render_with_diffusers.py
from __future__ import annotations
from pathlib import Path
import argparse, json, torch

def render_one(job_dir: Path, model_id: str, steps: int, guidance: float, width: int, height: int):
    rdir = job_dir / "render"
    prompt = (rdir/"prompt.txt").read_text(encoding="utf-8")
    negative = (rdir/"negative.txt").read_text(encoding="utf-8")
    meta = json.loads((rdir/"meta.json").read_text(encoding="utf-8"))
    seed = int(meta.get("seed", 0)) or 42

    device = "cuda" if torch.cuda.is_available() else "cpu"
    # AutoPipeline は多くのSD系モデルに対応（ローカルパスも可）
    from diffusers import AutoPipelineForText2Image
    pipe = AutoPipelineForText2Image.from_pretrained(model_id, torch_dtype=torch.float16 if device=="cuda" else torch.float32)
    pipe = pipe.to(device)

    generator = torch.Generator(device=device).manual_seed(seed)
    image = pipe(prompt=prompt, negative_prompt=negative, num_inference_steps=steps,
                 guidance_scale=guidance, width=width, height=height, generator=generator).images[0]
    out = rdir / "preview.png"
    image.save(out)
    print("rendered:", out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--jobs", nargs="+", required=True, help="job dirs or globs")
    ap.add_argument("--model", default="stabilityai/sdxl-turbo")  # or local folder
    ap.add_argument("--steps", type=int, default=12)
    ap.add_argument("--guidance", type=float, default=3.0)
    ap.add_argument("--size", default="896x512")
    args=ap.parse_args()

    w,h = map(int, args.size.lower().split("x"))
    import glob
    hits=[]
    for pat in args.jobs: hits += [Path(p) for p in glob.glob(pat)]
    for hdir in sorted(set(hits)):
        if hdir.is_file(): hdir=hdir.parent
        if (hdir/"render/prompt.txt").exists():
            render_one(hdir, args.model, args.steps, args.guidance, w, h)
        else:
            print("skip (no render/prompt.txt):", hdir)

if __name__=="__main__":
    main()
