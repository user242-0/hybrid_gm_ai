# GM-AI Dual Architecture

**Blueprint Intelligence × Deterministic Machine Core**

- 文書種別：将来アーキテクチャ方針／設計上の羅針盤
- 本格適用開始の目安：Session 60以降
- 直近の優先事項：Session 59でRCの認知行動ループを一度通す
- 配置先：`general_documents/future_goals/DUAL_ARCHITECTURE.md`

---

## 1. この文書の目的

この文書は、GM-AIの将来的なアーキテクチャ方針を記録するものである。

GM-AIは、次の相反する二つの性質を同時に保持する必要がある。

1. **Blueprint Intelligence**  
   RCの認知、記憶、belief、intent、シナリオルール、LLM連携などを柔軟に試行・進化させる、意味解釈中心の層。

2. **Deterministic Machine Core**  
   commandを厳密に検証し、world stateを更新し、Operationを進行させ、整合性と再現性を守る、決定的実行中心の層。

本構想の目的は、ただちにGM-AIを別言語へ全面移植することではない。

まず現在のPython実装を整理し、安定した実行責務を将来切り離せる状態にする。その後、必要性と効果が確認できた範囲だけをRustなどのネイティブ言語へ移す。

基本イメージは次の通り。

> Blueprintは夢を見て、意味を解釈し、行動を提案する。  
> Machine Coreは、その提案が世界で成立するか検証し、許された変化だけを実行・記録する。

---

## 2. Unity／スマホ連携に有効な理由

Dual Architectureは、将来GM-AIをUnity、スマートフォン、Web、複数クライアントへ接続する際に特に有効である。

将来のUnityクライアントは、RC_AI内部の認知処理すべてを理解する必要はない。次のことができればよい。

- プレイヤーまたはRCのcommandを送信する
- commandの受理または拒否結果を受け取る
- world stateの更新を受け取る
- DomainEventを受け取る
- キャラクター、場所、HUD、アニメーション、音、演出を表示する
- 既存のsimulation stateへ再接続する
- 必要に応じて重要な進行を再現する

同様に、GM-AIの認知・判断層も、PySide、UnityのGameObject、スマホUIなど、特定の描画環境へ直接依存すべきではない。

将来的には次のような構成を取れる。

```text
Unity / Mobile / Web / Debug HUD
              │
              ▼
        Adapter / API Boundary
              │
              ▼
┌────────────────────────────────────────┐
│ Blueprint Intelligence                 │
│ cognition / belief / memory / intent  │
│ advisory / LLM / scenario meaning     │
└───────────────────┬────────────────────┘
                    │ CoreCommand
                    ▼
┌────────────────────────────────────────┐
│ Deterministic Machine Core             │
│ validation / state transition         │
│ Operation execution / DomainEvent     │
│ invariants / replay                   │
└───────────────────┬────────────────────┘
                    │ CoreResult / Events
                    ▼
         World presentation and feedback
```

この分離により、Unityは強力な描画・操作クライアントになれる一方で、GM-AIの知能や正本となるworld stateをUnityへ閉じ込めずに済む。

スマートフォンでは、軽量なクライアントが描画と入力を担当し、重い認知処理やsimulationをPC側、ローカルプロセス、またはリモートサーバー側へ残す構成も可能になる。

---

## 3. 中心原則

本構想における中心的な区別は、次のようなものではない。

- PythonかRustか
- prototypeかproductionか
- 新版か旧安定版か

重要なのは、処理の責務である。

> **その処理は「何を意味するか」「何をしたいか」を決めているのか。**  
> それとも、  
> **「実行してよいか」「実行すると世界がどう変わるか」を決めているのか。**

前者は基本的にBlueprint候補である。  
後者は基本的にMachine Core候補である。

初期段階では、両方をPythonで実装してよい。

言語分離より先に、責務分離、境界契約、テスト、決定性を成立させる。

---

## 4. Blueprint Intelligence

Blueprint Intelligenceは、柔軟で意味解釈を中心とするGM-AIの知能層である。

### 主な責務

- RCごとの知覚と解釈
- `perceived_world`
- memoryの形成・参照
- beliefの生成、強化、矛盾、修正
- 感情・動機状態
- ActorModeの意味解釈
- intent生成
- preferred action選択
- advisory生成
- LLMへの入力と出力の解釈
- narrative interpretation
- Operation候補生成
- シナリオルールや定義の動的差し替え
- novelty、曖昧さ、人格差、「にじみ」
- プレイヤー向けの説明
- Intelligence Panelなどへの認知表示

### Blueprintが答える問い

- このRCは何が起きたと思っているか
- このRCはどのfactを信じているか
- 同じ出来事を刑事はどう解釈するか
- 同じ出来事を愉快犯はどう解釈するか
- このRCは次に何をしたいか
- どのOperationが有望に見えるか
- Machine Coreの結果をプレイヤーへどう説明するか

### 重要な制約

Blueprint Intelligenceは、intentやpreferred actionを選んだだけで、正本となるworld stateを直接書き換えてはならない。

Blueprintは提案またはcommandを提出する。  
実行の可否判定とstate更新はMachine Coreへ委ねる。

---

## 5. Deterministic Machine Core

Deterministic Machine Coreは、厳格で実行を中心とするGM-AIの基盤層である。

### 主な責務

- actionの存在確認
- command schemaの検証
- actorの権限とeligibility
- location、距離、接触条件の検証
- resource、inventory、status条件の検証
- active Operationとの競合確認
- ActionPipelineの再検証
- 正本となるworld stateの更新
- Operationの開始、phase進行、中断、完了
- MiniGoalの達成判定
- 二重実行、古いcommand、重複処理の防止
- state invariantの維持
- save dataの整合性
- 決定的なDomainEventの発行
- command log
- replayと再現性
- 外部クライアント向けの安定した実行契約

### Machine Coreが答える問い

- このcommandは現在合法か
- actorは正しいlocationにいるか
- 必要なitemや状態を持っているか
- 対象Operationはすでにactiveまたはcompleteではないか
- どのstate値をどう変更するか
- どのDomainEventを発行するか
- 同じ入力から同じ結果を再現できるか

### 重要な制約

Machine Coreは、その行動が感情的に魅力的か、物語として面白いか、人格にふさわしいかを決めない。

決められた規則に従い、合法な処理だけを正確に実行する。

---

## 6. 二つの層の関係

想定する基本フローは次の通り。

```text
World facts / observations
          │
          ▼
RC perception and belief
          │
          ▼
Memory / emotion / ActorMode
          │
          ▼
Intent
          │
          ▼
Preferred action / advisory
          │
          ▼
CoreCommand
          │
          ▼
Machine Core validation and execution
          │
          ▼
CoreResult + DomainEvents
          │
          ▼
World state / memory / belief / presentation
```

Machine Coreは、RC_AIまたはLLMから出力されたという理由だけで、Blueprintの提案を信用しない。

preferred actionも、正規の実行経路を通り、現在時点のstateに対して再検証されなければならない。

現在のGM-AIではすでに、RC_AI advisoryを手動採用した後、ActionPipelineで再検証してから実行している。

これはDual Architectureの初期形とみなせる。

---

## 7. 境界データ

二つの層は、暗黙的な共有状態の書き換えではなく、明示的なデータ契約で通信することが望ましい。

将来候補となる概念を以下に示す。

### `CoreCommand`

```text
request_id
actor_id
action_id
parameters
expected_state_version
timestamp または simulation_tick
random_seed（乱数が必要な場合）
source
```

### `CoreResult`

```text
accepted
rejection_code
rejection_details
new_state_version
state_patch または resulting_state
emitted_events
```

### `DomainEvent`

例：

```text
ActionAccepted
ActionRejected
ActorMoved
ItemConsumed
DiscoveryCreated
ActorModeChanged
OperationStarted
OperationPhaseAdvanced
MiniGoalCompleted
OperationCompleted
```

正確なfield定義は、Session 60のリファクタリング時に、実際のGM-AIのdata flowを確認してから決定する。

---

## 8. Operationの責務分割

Operationは、BlueprintとMachine Coreの両方にまたがる可能性が高い。

### Blueprint側

- Operationを提案する
- narrative上の目的を解釈する
- 複数候補から選択する
- RCにとっての重要度を評価する
- シナリオ固有定義を動的に読み込む
- なぜそのOperationが重要か説明する

### Machine Core側

- 開始条件を検証する
- 正本となるactive Operation instanceを作る
- phaseとMiniGoalの遷移を判定する
- costとeffectを適用する
- 不正な重複開始や競合を防ぐ
- 中断、失敗、完了を記録する
- 再現可能なDomainEventを発行する

指針：

> BlueprintがOperationを提案する。  
> Machine Coreが、そのOperationを世界内で合法に成立・進行させる。

---

## 9. 動的定義とCoreの固定性

「動的」であることは、実行中にPythonやRustのsource code自体を書き換えることを必ずしも意味しない。

優先して動的に差し替える候補：

- scenario pack
- rule data
- Operation定義
- intent定義
- action parameter
- state transition table
- 検証可能なDSL文書
- 明示的interfaceを持つplugin

Machine Coreは、新しい定義をschemaおよびcapabilityに照らして検証し、許可されたものだけを受け入れる。

これにより、Blueprintの柔軟性を保ちながら、正本となる実行ロジックの無秩序な自己改変を防げる。

---

## 10. 性能上の考え方

Python Blueprintとnative Machine Coreは、境界を適切に設計すれば、許容できないほど遅くなるとは限らない。

避けるべきなのは、fieldを一つずつ問い合わせるような細かすぎる境界通信である。

避けたい例：

```text
locationを取得
actor modeを取得
Operation状態を取得
action eligibilityを取得
```

望ましい例：

```text
validate_and_apply(command, current_state)
```

一度の呼び出しで、まとまった結果を返す。

```text
accepted
state changes
events
rejection reason
```

想定できる導入段階：

1. **すべてPython、同一process**  
   責務だけを論理的に分離する。

2. **Python＋native module、同一process**  
   一部の決定的処理のみRust化し、Python関数に近い形で呼び出す。

3. **別local process**  
   BlueprintとCoreがIPCで通信する。

4. **authoritative Core service**  
   Unity、スマホ、Web、Blueprint serviceが安定したAPIを通して通信する。

実測と必要性が確認される前に、段階2～4へ進まない。

---

## 11. Rustを候補とする理由

Cは小さく高速なnative codeを生成できる一方、memory safetyやundefined behaviorに関する新しい危険も持ち込む。

Machine Core候補としては、次の理由からRustの方が思想に合う可能性がある。

- memory safety
- explicit ownership
- strict type
- controlled concurrency
- native performance
- 安定したlibrary boundary

ただし、言語選択は二次的である。

責務が混ざったRust Coreより、責務が分離されたPython Coreの方が価値が高い。

最初の目標はnative compilationではなく、architecture上の決定性と境界の確立である。

---

## 12. 現在のGM-AIへの仮マッピング

現時点での暫定分類：

| 現在の領域 | 将来の傾向 | 理由 |
|---|---|---|
| `RCContextBundle` | 境界／Blueprint入力 | 認知判断用contextを束ねる |
| RC_AI intent | Blueprint | 意味解釈と行動選択 |
| preferred action / advisory | Blueprint | 実行命令ではなく提案 |
| Intelligence Panel | Presentation／Blueprint adapter | 認知内容の説明 |
| advisory手動採用 | 境界 | 提案を実行要求へ変換する |
| ActionPipeline検証 | Machine Core候補 | authoritativeなeligibility確認 |
| world-state effect適用 | Machine Core候補 | 整合性の中心となるmutation |
| Operation phase進行 | Machine Core候補 | 決定的な状態遷移 |
| MiniGoal達成判定 | Machine Core候補、一部Blueprint入力 | 進行結果はauthoritativeである必要がある |
| `perceived_world` | Blueprint | RC相対の世界解釈 |
| belief / memory | Blueprint | 主観的認知 |
| canonical world facts | Machine Core／authoritative state | 全体で共有する現実 |
| scenario定義 | Blueprint data | 動的に差し替えたい |
| scenario定義の検証 | Machine Core候補 | 不正な定義を拒否する |
| HUD / PySide GUI | Client adapter | simulationの正本を持たせない |
| Unity presentation | 将来のClient adapter | 描画とcommand送信を担当 |
| save整合性 / replay | Machine Core候補 | 再現性が必要 |

この分類は暫定であり、認知行動ループ完成後に再評価する。

---

## 13. Session 59での扱い

Session 59をDual Architectureのリファクタリングセッションにしてはならない。

Session 59の主目的は次の通り。

> RC memoryとbeliefを更新・反映し、一度の認知行動ループを最後まで通す。

Session 59では、この文書を軽い制約としてのみ参照する。

1. beliefとmemoryはRC相対の認知情報として扱う
2. RC_AIやbelief処理からActionPipelineを迂回してauthoritative world stateを変更しない
3. 実行結果を、memoryとbeliefが受け取れるfactまたはeventとして表現できるよう意識する
4. 認知行動ループ完成前に、不要な大規模抽象化へ踏み込まない

Session 59は、将来の完璧な境界を作ることより、ループを最後まで動かして観察することを優先する。

---

## 14. Session 60以降の導入案

Session 59で一度の認知行動ループを成立させた後、Dual Architectureを設計上の羅針盤として大規模リファクタリングを開始する。

### Session 60：Architecture Inventory／Boundary Map

次を分類・記録する。

- Blueprint責務
- Machine Core候補
- Client／Adapter責務
- 境界データ
- authoritative stateへの直接書き込み箇所
- circular dependency
- Unity／スマホ連携上の制約
- GUI依存箇所
- save／replayへ影響する非決定的処理

この段階ではRust化を開始しない。

### Session 61：薄いCommand／Result境界

Python上で最小限の次の形式を導入する。

- `CoreCommand`
- `CoreResult`
- `DomainEvent`

既存ActionPipelineを薄く包み、挙動は変えない。

### Session 62：無秩序なstate mutationの削減

authoritative stateを直接書き換えている箇所を調査し、優先領域から明示的なmutation functionまたはhandlerへ通す。

優先候補：

- ActionPipeline effect
- Operation phase進行
- MiniGoal更新
- actor location変更
- actor mode変更
- discovery／factの昇格

### Session 63：Deterministic Replayの基礎

次の組み合わせから、同じstateとevent列が再現されることをテストする。

```text
initial state
+ ordered commands
+ explicit randomness
= same resulting state and events
```

Core候補から、制御されていないclock、random、UUID生成、GUI stateへの依存を取り除く。

### Session 64以降：小さなRust Proof of Concept

安定した契約とテストが成立した後で、純粋で小さく、効果を測りやすい関数を一つだけRustへ移す。

候補：

- requirement evaluation
- actor/location eligibility
- state invariant check
- 単純なOperation transition validation

同じfixtureをPython版とRust版に渡し、結果が一致することを確認する。

複雑さに対して利益が少ない場合は、移植を止めてもよい。

---

## 15. リファクタリング時の原則

Session 60以降は、次の原則を守る。

1. **判断と実行を分ける。**
2. **認知処理からauthoritative world stateを直接変更しない。**
3. **stateを変更する入口を明示する。**
4. **境界をまたぐdataは粗粒度にまとめる。**
5. **CoreからUIを直接操作せず、DomainEventを返す。**
6. **scenario固有の意味をgeneric execution engineへ埋め込みすぎない。**
7. **決定的経路では、timeとrandomnessを明示的入力にする。**
8. **一部を移植する間はPython reference implementationを残す。**
9. **最適化やRust化の前に計測する。**
10. **`main`はsource of truthとして維持し、機械語binaryはbuild artifactとして扱う。**
11. **Unity、PySide、スマホUIをsimulation truthの所有者にしない。**
12. **大規模な一括書き換えではなく、境界ごとに段階移行する。**

---

## 16. Non-Goals

本構想は、現時点で次を要求しない。

- GM-AI全体のRustまたはCへの全面移植
- 二つの完全なGM-AI実装の恒久的な二重保守
- 全subsystemのmicroservice化
- すべての処理の決定論化
- LLMの排除
- runtime中のsource code自己書き換え
- Unity固有描画処理のMachine Coreへの移動
- Session 59完了前の大規模リファクタリング開始
- 性能問題が確認されていない領域の先行最適化

---

## 17. 長期像

成熟したGM-AIは、将来次のような構造を取れる。

```text
Human / Player
      │
Unity / Mobile / Web / Debug Client
      │
      ▼
Blueprint Intelligence
- RC perception
- memory and belief
- emotion and intent
- LLM interpretation
- advisory and Operation proposal
      │
      ▼
Deterministic Machine Core
- command validation
- authoritative state transition
- Operation execution
- DomainEvent
- save consistency and replay
      │
      ▼
World State
      │
      └──── perception / memory / belief / presentationへfeedback
```

Machine Coreは、世界の骨格と法則である。  
Blueprint Intelligenceは、世界の想像力、解釈、進化する神経系である。

長期目標は、GM-AIを機械語の中へ凍結することではない。

> 柔軟な知能層を保ちながら、simulation worldへ厳格で移植可能かつテスト可能な実行核を与える。

---

## 18. Decision Summary

- **GM-AI Dual Architecture**を将来設計方針として採用する
- **Blueprint Intelligence × Deterministic Machine Core**を、言語分割より先に責務分割として扱う
- Session 59では、認知行動ループ完成を優先する
- Session 59では本書を軽く参照するだけに留める
- Session 60以降、本書を設計上の羅針盤としてarchitecture inventoryと大規模リファクタリングを開始する
- Unity／スマホ連携に備え、境界、authoritative state、DomainEvent、決定的実行、UI非依存契約を整える
- Rust／Cへの移植は、小さなCore境界が安定し、テストされ、実利が確認された後に判断する
