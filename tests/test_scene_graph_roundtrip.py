from pathlib import Path
import yaml
from utility.config_loader import job_root_from_cfg
from schemas.scene_graph import ObjectSpec, Pose  # 手元のモデルに合わせて調整

def test_scene_graph_roundtrip_minimal():
    job_root = job_root_from_cfg()
    yml = job_root / "scene_graph.yml"
    assert yml.exists(), f"missing: {yml}"
    data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}

    # objects 部分を Pydantic で検証
    objs = data.get("objects") or []
    parsed = []
    for o in objs:
        pose = o.get("pose")
        pose_obj = Pose(**pose) if isinstance(pose, dict) else None
        kw = {k: v for k, v in o.items() if k not in ("pose",)}
        parsed.append(ObjectSpec(pose=pose_obj, **kw))
    assert len(parsed) == len(objs)

    # meta/outputs の最低限チェック
    meta = data.get("meta") or {}
    outputs = data.get("outputs") or {}
    assert "commit" in meta and meta["commit"], "meta.commit missing"
    assert "seed" in (outputs.get("image") or {}), "outputs.image.seed missing"
    # why_now は prod/lab ポリシーで省略可能にしているなら existsチェックは任意

    # 再ダンプ→読み直し（syntacticに壊れていないか）
    dumped = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    data2 = yaml.safe_load(dumped)
    assert data2.get("objects"), "objects lost on dump/load"
