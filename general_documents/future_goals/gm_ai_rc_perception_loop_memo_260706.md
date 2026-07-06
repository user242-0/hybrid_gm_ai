# GM-AI：RC別 perceived_world と最小ナラティブループ設計メモ

## 目的

GM-AIを、単なるHUDアクション提示システムではなく、個々のRC（Reversible Character）がそれぞれの視点・記憶・目的を持って活き活きと動くナラティブシミュレーションへ発展させる。

その第一歩として、`director_world` の真実をRCが直接見るのではなく、RCごとに変換された `perceived_world` を通して世界を見る構造を導入する。

---

## 現在の実装フェーズ

現在は、HUDアクションからActive Operationを立ち上げる最小スケルトンを実装した段階。

次の短期タスクとしては、まずGUIアクションの基礎動詞を補強する。

例：

- 見る / 観察する
- 調べる
- 聞く / 聞き込みする
- 移動する
- 照合する
- 待つ / 様子を見る
- 隠す
- 逃げる

この基礎動詞群は、将来的にLLM/RC_AIが高度な行動意図を出した場合でも、最終的にシステムが実行可能なaction/operationへ落とすための土台になる。

---

## 目指す最小ループ

GM-AIがRCごとの認識・行動・記憶更新を行うための最小ループは、以下の7段階。

```text
① director_world
    ↓
② RCごとの perceived_world を生成
    ↓
③ RCの記憶・感情・actorMode・MiniGoalと統合
    ↓
④ LLM / RC_AI が次の認識・葛藤・行動意図を出す
    ↓
⑤ システム側が実行可能な operation/action に変換
    ↓
⑥ 結果が director_world に反映
    ↓
⑦ RCの記憶とbeliefが更新される
```

この中で、特に重要なのは②の `perceived_world`。

`director_world` は世界の真実を保持するが、RCはそれを直接見るのではなく、自分の立場・知識・actorMode・過去の記憶に応じて変換された世界を見る。

---

## ② perceived_world の意義

`perceived_world` は、LLMに投げるためのプロンプト素材というだけではない。

むしろ、GM-AIにおける「RCごとの世界の見え方」を定義する投影レイヤである。

```text
director_world = 世界の真実
perceived_world = そのRCから見えている世界
belief_world = そのRCが信じている世界
```

最初は `belief_world` まで厳密に分けなくてもよい。
まずは `build_perceived_world(actor_id, director_world)` を作り、RCごとに見える情報・見えない情報・疑っている情報を分ける。

---

## 例：同じ事件を刑事RCと愉快犯RCが別々に見る

### director_world 側の真実

```text
- 目撃者Aは「20時頃に見た」と証言している
- 監視カメラ記録では20時05分になっている
- 実は監視カメラの時計が5分ズレている
- 愉快犯はその時刻ズレを知っている
- 刑事はまだ時刻ズレを確定していない
- 目撃者Aは動揺している
```

### 刑事RCの perceived_world

```text
- 目撃者Aの証言と監視カメラ記録にズレがある
- 原因はまだ不明
- 監視カメラの時刻、または証言内容に違和感がある
- ここを照合すれば突破口になるかもしれない
```

### 愉快犯RCの perceived_world

```text
- 監視カメラの時刻ズレは自分に有利に働いている
- 刑事が照合に進むと危険
- 目撃者Aが崩れると時刻トリックが露見する可能性がある
- 今のうちに別の痕跡を残すか、目撃者との接触を避けたい
```

同じ `director_world` でも、RCごとに世界の見え方が変わる。
これにより、RCは神視点ではなく、自分の立場から誤解し、疑い、判断し、行動する存在になる。

---

## 最短ロードマップ

### Step 1：GUIアクション基礎動詞を補強する

まずはRCが世界に触るための最小アクション群を整える。

候補：

```text
inspect / observe
ask / interview
move
compare
wait
hide
flee
```

ここではまだGUIアクションコンパイルの本実装までは行わない。
あくまで将来のaction/operation解決に使える基礎動詞を増やす。

---

### Step 2：director_world内のfact形式を少し整理する

`perceived_world` を作るために、世界内の事実に最低限のメタ情報を持たせる。

例：

```text
Fact:
  id
  kind
  location
  truth_value
  known_by
  discoverable_by
  visible_to
  tags
  importance
  actor_labels
```

最初は厳密でなくてよい。

例：

```text
camera_clock_skew:
  known_by: ["trickster"]
  discoverable_by: ["detective"]
  tags: ["camera", "time", "evidence"]
  importance: 0.8
```

---

### Step 3：build_perceived_world(actor_id, director_world) を作る

最初はLLM不要。
ルールベースでよい。

例：

```text
if actor_id == "detective":
    - detective が known_by に含まれるfactを表示
    - detective が discoverable_by に含まれるfactを「違和感」「疑い」として表示

if actor_id == "trickster":
    - trickster が known_by に含まれるfactを表示
    - detective の進行度に応じて「危険」「露見リスク」を表示
```

この段階の目標は、同じ `director_world` から、刑事と愉快犯で異なる `perceived_world` が出ること。

---

### Step 4：RCContextBundle を作る

`perceived_world` だけではなく、RCの現在状態をひとまとめにする。

```text
RCContextBundle:
  actor_id
  actor_profile
  actor_mode
  micro_goal
  active_operation
  perceived_world
  recent_memory
  available_actions
```

この構造を作ることで、RC_AIやLLMに渡す情報が安定する。

---

### Step 5：rc_ai.py は advisory から始める

いきなり自動実行させない。
まずはRC_AIが「認識・葛藤・行動意図」を出すだけに留める。

出力例：

```text
rc_ai_output:
  interpretation: "証言と映像のズレが突破口になりそうだ。"
  tension: "ただし、誤認なら捜査が空転する。"
  desired_intent: "camera_time_check"
  preferred_action_id: "compare_camera_time"
```

RC_AI/LLMに任せるのは以下まで。

```text
- どう見たか
- 何を気にしたか
- 次に何をしたがっているか
- どのaction/operation候補を選びたいか
```

逆に、以下はシステム側が握る。

```text
- 世界の真実
- 実行可能な行動
- 行動の成否
- director_worldの更新
- Active Operationの進行
- memory / belief の保存
```

---

### Step 6：行動意図を既存HUD/GUIアクション/Operation候補に接続する

RC_AIが `preferred_action_id` を出した場合でも、必ずシステム側で検証する。

検証項目：

```text
- そのaction_idは存在するか
- 現在のactor_idで使えるか
- 現在のactorModeで許可されるか
- location/discovery条件を満たすか
- active_operationに接続できるか
```

通れば候補として提示。
最初は自動実行ではなく、HUD上の提案に留めるのが安全。

例：

```text
AI提案：
「監視カメラの時刻ズレを照合する」
[実行]
```

---

### Step 7：実行結果を director_world と memory / belief に返す

例：

```text
compare_camera_time 実行
↓
director_world に camera_skew_noticed_by_detective を追加
↓
detective memory に「監視カメラの時刻ズレに気づいた」を追加
↓
次回 build_perceived_world で刑事の見え方が変わる
```

ここまで通ると、RCは単にアクションを選んだだけではなく、

```text
見た
疑った
行動した
世界を変えた
記憶した
次の見え方が変わった
```

という一周を経験する。

これが、GM-AIをRCごとのナラティブシミュレーションにする第一歩になる。

---

## 推奨セッション順

```text
Session 53:
  GUI基礎動詞の補強
  ※GUIアクションコンパイル本実装までは行わない

Session 54:
  RC別 perceived_world 最小縦切り

Session 55:
  RCContextBundle 実装
  perceived_world + actorMode + MicroGoal + ActiveOperation + memory を統合

Session 56:
  rc_ai.py で advisory 的に認識・葛藤・行動意図を出す

Session 57:
  行動意図を既存HUD/GUIアクション/Operation候補へ接続

Session 58:
  実行結果を director_world と RC memory / belief に反映
```

---

## 推奨モジュール分担

```text
director_world.py
  世界の真実を保持する

perceived_world.py / perception.py
  actor_idごとに世界を投影する

rc_context.py
  perceived_world + actorMode + MicroGoal + memory + active_operation を束ねる

rc_ai.py
  RCの認識・葛藤・行動意図を出す

operation.py
  HUDアクションから立ったActive Operationを管理する

actions/
  GUI基礎動詞、HUDアクション、実行可能アクション群

rc_memory.py / memory.py
  RCごとの記憶・belief更新

ro.py
  RC_AIに対する大局的判断・優先度補正・行動方針パッチを扱う候補
```

---

## 最小縦切りの名前案

```text
RC Perception Loop v0
```

または、

```text
Session54: RC別 perceived_world 最小縦切り
```

目標：

```text
同じ director_world から、
刑事と愉快犯で異なる perceived_world を生成し、
その違いがHUDアクション候補・MicroGoal・ActiveOperation・RC_AI提案に影響する。
```

---

## RO（Reversible Operator）についての補足

ROは、もともと「RC_AIに対して大局的判断として行動優先リストパッチを出す、RCに対するオペレータ」という意味を含めた概念。

今後、③④のRC_AIが高度化すると、ROが一部オーバーエンジニアリングに見える可能性はある。
ただし、完全に不要とは限らない。

RC_AIが「個々のRCの内面・認識・行動意図」を担当するなら、ROは以下のような参謀・補正役として残せる。

```text
RC_AI:
  そのRC自身の視点から、どう見え、何をしたいかを考える

RO:
  シナリオ全体・RC間関係・緊張感・進行バランスを見て、
  行動優先度や方針にパッチを当てる
```

つまり、ROは「RCの心そのもの」ではなく、「RC_AIへの方針補正・優先度補正・戦術パッチ」と位置づけるとよい。

### 命名について

`Reversible Operator` は思想としては面白いが、初見ではやや分かりづらい。

候補：

```text
RO: Reversible Operator
  既存名を維持。思想性は強いが説明が必要。

RC Operator
  RCに対するオペレータだと分かりやすいが、RCの行動全体を司るように見える恐れがある。

RC Strategy Operator
  参謀・戦術補正役として分かりやすい。

Priority Patch Operator
  行動優先度パッチを出す役割が明確。

RC Advisory Operator
  RC_AIへの助言・補正役として分かりやすい。
```

現時点では、内部名として `RO` を維持しつつ、ドキュメント上では以下のように説明するのが安全。

```text
RO（Reversible Operator）:
RC_AIに対して、シナリオ進行・RC間関係・actorMode・Operation状況を踏まえた
行動優先度パッチ / 方針補正を与える参謀レイヤ。
RCの行動を直接支配するものではなく、RC_AIの判断に影響を与える補助オペレータ。
```

将来的に名前を変えるなら、`RC Strategy Operator` または `RC Advisory Operator` が分かりやすい。
ただし、現段階では無理に改名せず、ROの責務を小さく定義しておくのがよい。

---

## 一文まとめ

GM-AIの次の重要ステップは、LLMに高度なRC演技をさせることではなく、まず `director_world` をRCごとの `perceived_world` に投影し、RCが自分の視点から世界を見て、疑い、行動し、記憶し、次の世界の見え方が変わる最小ループを一度通すことである。

## 重要補足

まずはfact新設より、既存のdiscoveries/opportunitiesをperceived_world_v0の材料にする。将来、必要になったらfact層をdirector_world側に追加する。

perceived_world設計では、factをゼロから大規模に作るのではなく、既存のdiscoveries / opportunitiesを活かす。ただし、discoveryを即director_worldの確定factに昇格させるのは避ける。

まずは、director_world側には中立的なWorldFactを置き、RCごとの発見・解釈・仮説はDiscovery / Claim / Beliefとして保持する。調査やoperation結果を通じて、必要なclaimだけがConfirmed Factに昇格する。

例：割れた窓はWorldFactとしては「窓が割れている」に留める。刑事RCは「侵入経路かもしれない」と解釈し、愉快犯RCは「偽装工作として利用した」と認識する。どちらの解釈が世界factへ昇格するかは、後続の調査・operation・行動結果で決める。

### 実装上の注意：perceived_worldは最初は保存しない

perceived_world_v0 は、director_world / actor_discoveries / actor_locations / actor_modes / active_operation から都度生成する派生ビューとする。
初期段階では perceived_world 自体を save/load 対象にしない。
保存するのは actor_discoveries / memory / belief / director_world 側の状態であり、perceived_world はそれらから再構築する。

### Session53での扱い

Session53では perceived_world 本実装には入らない。
ただし、将来 build_perceived_world の入力になるよう、GUI基礎動詞は actor_locations / actor_discoveries / active_operation など、actor別状態を正しく更新する方針で実装する。

### メタ認識の扱い

「Aが知ったことをBが知る」系のメタ認識は、汎用階層として自動生成しない。
初期段階では、物語上必要なものだけを明示discovery / claimとして定義する。

例:
- trickster_knows_fiber_collected
- detective_notices_false_trace
- trickster_realizes_witness_saw_face