# Architecture (v0)

## 0. One-minute overview
（あとで1段落）

## 1. Data flow (1 loop)
Input → Director → HUD/GUI → Action → World update → Director → SceneGraph

## 2. Components (責務とI/O)
- Director
- RC_AI
- action_definitions
- action_registry
- packs
- simulation loop
- HUD / old GUI / CLI
- scene_graph emitter

## 3. What is scenario-specific vs core?
### Core (shared)
- RC_AI（スコアリング）
- registry（effects適用）
- emitter（scene_graph出力）
- director（goal選択とscene注入の枠）

### Scenario (pack)
- actions（label/time/emotion_delta/effects）
- goals/modes/minigoals
- scene_templates（scene_idの文章や登場物）

### Bridge (coreだけどパックに依存して読込む)
- pack registry（premise-text→pack）
- pack loader（YAML→正規化）

## 4. Current seams / extension points
- Where to inject scenes
- Where to score actions
- Where to load world defaults

## 5. TODO (next sessions)
- UI unification
- World loader
