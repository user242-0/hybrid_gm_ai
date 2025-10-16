# src/datalab/emitters/scene_graph_emitter.py
from pathlib import Path
from datetime import datetime
import yaml
from schemas.scene_graph import SceneGraph, ObjectSpec, Pose

def emit_scene_graph(job_root: Path, theme: str, background: str, objects: list, loras: list):
    sg = SceneGraph(
        project_id=f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        theme=theme,
        background=background,
        lora_styles=loras,
        constraints={"avg_triangle_budget": 10000, "world_scale": "meters"},
        objects=objects,
        outputs={"image": {"resolution":"768x768","steps":30,"guidance":7.5}}
    )
    job_root.mkdir(parents=True, exist_ok=True)
    (job_root / "scene_graph.yml").write_text(
        yaml.safe_dump(sg.model_dump(), allow_unicode=True)
    )
