
-----------------------------------------------------------
決定：**Session 60-1へ進んでよい**

ただし、Session 60-0Bは「不要になったので飛ばす」ではなく、

> **議論によって目的を達成したため、縮約版として完了させる**

という扱いがよいと思います。

---

# 1. 目標形そのものが「見通しの良さ」になっているか

なっています。


GameCommandService
  ↓
ActionPipeline
  ↓ ActionOutcome
OperationRuntime
  ↓ OperationTransition[]
MemoryProjection
  ↓ MemoryRecord[]
BeliefProjection
  ↓ BeliefUpdate[]
fresh RCContextBundle


この形では、上から順番に読むだけで、

* 何が入力されたか
* 誰が何を判断したか
* 誰が正本を書き換えたか
* 次の段階へ何を渡したか
* どこで失敗したか

を説明できます。

たとえば、

```text
ActionPipeline
「Actionは成功し、effectsはworldへ適用された」

OperationRuntime
「その結果、MiniGoalが達成されOperationが進行した」

MemoryProjection
「そのTransitionを刑事の経験として記録した」

BeliefProjection
「そのMemoryを根拠にBeliefを更新した」
```

と、各段階を一文で説明できます。

これはまさにSession 60-0Bで求めていた、

```text
一本道が見える
責務が一文で言える
入出力が見える
正本writerが見える
```

という「見通しの良さ」です。

---

# 2. ただし、60-0Bのすべてが自動的に終わったわけではない

目標形を立てたことで、60-0Bの中心問題はほぼ解決しました。

しかし、次の約束は短くても明文化しておく必要があります。

## 60-0B完了条件

### ① 上位の一本道

```text
GameCommand
→ ActionOutcome
→ OperationTransition
→ Memory
→ Belief
→ fresh ContextBundle
```

この順序を基本経路として守る。

### ② 正本とwriter

```text
Action関連world state
→ Action domain writer

Operation state
→ OperationRuntime経由のOperation writer

Transition history
→ Operation transition recorder

Memory
→ MemoryProjection

Belief
→ BeliefProjection
```

### ③ 隠れたworld更新を増やさない

```text
HUD refresh
ContextBundle生成
HCP表示
trace表示
```

などのread系処理から、ゲームstateを変更しない。

現在のlegacy同期は既知の例外として記録し、将来隔離する。

### ④ 段階間は明示的なresultで接続する

```text
ActionOutcome
OperationTransition
MemoryRecord
BeliefUpdate
```

を渡し、下流処理が上流moduleの内部変数を直接読みに行かない。

### ⑤ HCPは観察者

HCPは各resultと正本の状態を読み、

* 誰が書いたか
* 何が契機だったか
* before／after
* どこまでcommitされたか

を表示する。

HCP自身は正本を書き換えない。人間の介入もformal commandとしてMachine Coreへ返す。これは添付文書の「Control Planeは第三のゲームエンジンでも、第二の正本でもない」という原則と一致しています。

### ⑥ Coreはheadlessで動く

```text
HUDが開いていなくても動く
Unityが接続されていなくても動く
HCPが表示されていなくても動く
```

ことを守る。

### ⑦ 黄金経路を維持する

```text
Action
→ Operation進行
→ Transition
→ Memory
→ Belief
→ fresh Bundle
```
のSession 59挙動をcharacterization testとして守る。
---
#  Unity・モバイル連携に必要な最終境界

将来は概ね次の構造が望ましいです。
Unity UI / Mobile UI / Python HUD / CLI
                ↓
             Adapter
                ↓
         GameCommandService
                ↓
      Deterministic Machine Core
       ├─ ActionPipeline
       ├─ OperationRuntime
       ├─ rules / validation
       └─ authoritative world mutation
                ↓
         Domain results / events
                ↓
      Blueprint Intelligence
       ├─ MemoryProjection
       ├─ BeliefProjection
       ├─ ContextBundle
       └─ RC_AI
---

#  PythonとUnityでCoreを二重化しない

この目標形の大きな価値はここにもあります。

Unity連携時に避けたいのは、

```text
Python版OperationRuntime
Unity C#版OperationRuntime
```

を別々に実装することです。

それをすると、いずれ、

```text
Pythonでは進む
Unityでは進まない

PythonとUnityでMiniGoal判定が違う
```

という二重正本になります。

当面は、

```text
Python側Machine Core
= 唯一のゲームルール実装

Unity／Mobile
= Adapter／表示／入力
```

とするのが安全です。

将来、本当にC#への移植が必要になった場合も、

ActionRequest
ActionOutcome
OperationTransition
GameCommandResult

というcontractが固まっていれば、挙動比較テストを作れます。

---

# 推奨ロードマップ

```text
Session 60-0
責務・正本・上位フロー・不変条件整理
        ↓
Session 60-1
OperationRuntime抽出
        ↓
Session 60-2
GameCommandService導入
        ↓
Session 60-3候補
ActionOutcome／GameCommandResult contract安定化
OperationStore／OperationInstance導入
        ↓
Session 60-4候補
最小HCP Operation Trace Spine
        ↓
Session 60-5候補
Core packageの物理分離
Adapter境界整理
        ↓
Unity／Mobile接続
```



> **直近目標**
> ActionPipelineからOperationの意味・進行・記録責務を外し、ActionOutcomeをOperationRuntimeへ渡す形へ整える。

> **Session 60-1ミニゴール**
> 既存のOperation開始・進行・transition記録をOperationRuntimeへまとめ、ActionPipelineから一回呼ぶ形にする。


-----------------------------------------------------------


