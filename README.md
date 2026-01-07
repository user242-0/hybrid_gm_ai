# Game Master AI (hybrid_gm_ai)

## What this is
Director層 + RC_AI + ActionSpec により、シナリオ(pack)を差し替えつつ
MicroGoal/Scene injection/Emotion(RGB)を伴うシミュレーションを回す実験プロジェクト。

## Quick start
### Install
- python -m venv venv
- pip install -r requirements.txt
(or pyproject.tomlに従う)

### Run
- python -m src.simulation
- python -m src.simulation --premise-text "..."

## Key concepts
- Director: micro-goal選定、シーン注入（packベース）
- RC_AI: mode + emotion + action deltas を用いた行動選択
- Emotion: (R,G,B) = (衝動,自己制御,優しさ)
- ActionSpec: legacy/new action定義を統一し、effectsでworldを変異させる
- Packs: data/director/packs/*.yml にシナリオ定義（modes/goals/actions/world_defaults）

## Action pipeline (post needle-extraction)
- execute_action: requirements → time → emotion_delta → effects → function → legacy fallback
- world defaults: pack.world_defaults が起動時に world にマージされる

## Directory layout (important only)
src/
  director/
  ui/
  rc_ai.py
  action_model.py
  action_effects.py
  action_definitions.py
  action_registry.py
data/director/packs/

## Tests
pytest
