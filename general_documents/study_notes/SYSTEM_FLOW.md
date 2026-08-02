director_world
↓ 世界の客観状態
perceived_world
↓ RCが認識できる範囲に投影
Context Bundle
↓ RC_AIが判断に使える形式へ整形
intent / advisory
↓ 何をしたいか
Operation / action
↓ 世界へ働きかける
progress record
↓ 行動結果を記録
memory / belief
↓ 経験・認識を更新
次回のRC_AI判断



---------------------------------
将来目標（Session60）
Human / RC_AI / GUI
        ↓
GameCommand
        ↓
GameCommandService
        │
        ├─ ActionPipeline
        │      └─ ActionOutcome
        │
        ├─ OperationRuntime
        │      ├─ OperationStore
        │      ├─ OperationInstance
        │      └─ OperationTransition[]
        │
        ├─ MemoryProjection
        │      └─ MemoryRecord[]
        │
        ├─ BeliefProjection
        │      └─ BeliefUpdate[]
        │
        └─ fresh RCContextBundle

Control & Legibility Layer
        └─ 各stageのresultを観察・表示