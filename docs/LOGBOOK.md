# LOGBOOK.md - 開発日誌（雑談OK）

ルール:
- 1エントリは短くていい（箇条書きでもOK）
- 「気持ち」+「技術メモ」+「次回の最初の一手」を1つ入れると最強
- 長文になったら、`general_documents/diary/` に退避してリンクを貼る

---
## 2026-06-15（Session 38-44: Action Proposal DSL → HUD read-only表示）

### 今日やったこと（結果）

* Action Proposal DSL v0.1 の validator contract を固定した。

  * `CHECK_ORDER = ("A_syntax", "B_uniqueness", "C_requirements", "D_effects", "E_safety", "F_narrative")`
  * `ValidationReport.reason_codes` を追加
  * `ValidationReport.to_dict()` を追加
  * `overall` は REJECT優先、全PASSならPASS、それ以外UNKNOWNの仕様で固定

* Shadow Adapterを実装した。

  * `validate_proposal_shadow(proposal, context=None) -> dict`
  * `append_shadow_log(path, record) -> None`
  * proposalを検問し、実行せず、結果をdict/JSONLで扱えるようにした

* Shadow Log Contractを固定した。

  * `SHADOW_LOG_FILENAME = "action_proposal_shadow.jsonl"`
  * 標準保存先: `jobs/%Y%m%d_quick/action_proposal_shadow.jsonl`
  * record schema: `action_proposal_shadow.v0.1`
  * `validate_and_build_shadow_record()` を追加
  * `jobs/` は完全な一時ゴミ箱ではなく、少なくとも一部はプレイセッション監査ログとして扱う必要が出てきた

* Advisory Adapterを実装した。

  * `build_advisory_item(shadow_record) -> dict | None`
  * `build_advisory_items(shadow_records) -> list[dict]`
  * `validate_proposal_to_advisory(...) -> dict | None`
  * PASS済みshadow recordだけをadvisory item化する
  * UNKNOWN / REJECT は表示候補にしない

* Advisory Feed / Display Contractを実装した。

  * `build_display_item(advisory_item)`
  * `build_advisory_feed(advisory_items, limit=5, run_id=None)`
  * `build_advisory_feed_from_shadow_records(...)`
  * `build_advisory_feed_from_shadow_log(...)`
  * HUDが読みやすい display item list に変換できるようにした

* Read-only Advisory Providerを実装した。

  * `get_advisory_feed(...)`
  * `get_advisory_display_items(...)`
  * `has_advisory_items(...)`
  * HUD側が「どのJSONLを読むか」を知らなくても、providerからitemsを取得できるようにした
  * providerは read-only。ログやgame_stateを書き換えない

* HUD Advisory read-only表示を実装した。

  * Director HUDに「AI提案」欄を追加
  * RO表示の下、Actions listboxの上に表示
  * `HUDCallbacks.refresh_hud()` から `get_advisory_display_items(limit=3)` をread-onlyに呼ぶ
  * 表示は最大3件
  * クリック不可・実行不可・Actions listboxには混ぜない
  * provider例外時はHUDを落とさず、AI提案欄をクリアする

### 確認できたこと

* action proposal系のtargeted testsは通過。
* HUD advisory表示テストも通過。
* `pytest -q` は既存と思われる3件で失敗。

  * `tests/test_npc_switch.py::test_npc_switch`
  * `tests/test_requirements_time_weather.py::test_statue_actions_are_gated_by_time_and_weather`
  * `tests/test_scene_graph_roundtrip.py::test_scene_graph_roundtrip_minimal`
* `python -m src.simulation` でHUD起動を確認。
* 手動で作成した `action_proposal_shadow.jsonl` から、HUDの「AI提案」欄に提案が表示されることを目視確認。
* 初回の手動PowerShellサンプルでは日本語が `?????` になったが、これは実装バグではなく、テストデータ作成時の文字コード問題だった。
* Unicode escapeでサンプルを作り直すと、日本語label/detailは正しく表示された。

### 気づき

* Action Proposal DSLは、ついに「提案→検問→ログ→HUD表示」まで到達した。
* ただし、まだ「提案を生成する主体」は本体に接続されていない。
* 現時点では、AI提案欄はshadow logにPASS済みrecordがある場合だけ表示される。
* 次にいきなり実行可能にするのではなく、まずはデモ用proposal生成・保存導線を作る方が安全。
* `jobs/%Y%m%d_quick/` は今後、完全な一時フォルダではなくなる。`action_proposal_shadow.jsonl` のような監査ログは保持対象として扱う。

### 次回の最初の一手

* Action Proposal Demo Producer / Seed を作る。

  * 手動PowerShellではなく、デモ関数またはdebug操作でproposalを1件作る
  * A-F validatorに通す
  * shadow logへ保存する
  * HUDのAI提案欄に表示されることを確認する
  * まだActionPipelineには接続しない
  * まだActions listboxには混ぜない

## 2026-06-14（Session 35-37: Action Proposal DSL Check D/E/F）

### 今日やったこと（結果）

* Action Proposal DSL v0.1 の Check D: Effects を実装。

  * `validate_proposal(..., known_effect_paths=None)` に拡張。
  * dict/list形式の effects を検査。
  * dict形式では key を effect path として扱う。
  * list形式では各 item の `op` / `path` 構造を検査。
  * `op` は `add` / `set` のみ許可。
  * world state への適用や registry/pipeline連携は未実施。
  * `pytest tests/test_action_proposal_validator.py -q`: 45 passed。

* Action Proposal DSL v0.1 の Check E: Safety を実装。

  * `validate_proposal(..., safety_limits=None)` に拡張。
  * `forbidden_effect_paths` による禁止path検査を追加。
  * `max_abs_delta` / `max_abs_delta_by_path` による add delta上限検査を追加。
  * `set` はdelta上限対象外。
  * 判定不能な add value は UNKNOWN。
  * world state参照や実適用は未実施。
  * `pytest tests/test_action_proposal_validator.py -q`: 62 passed。

* Action Proposal DSL v0.1 の Check F: Narrative を実装。

  * `validate_proposal(..., narrative_context=None)` に拡張。
  * source / rationale / modes / allowed_modes / tone_tags / tags / forbidden_tags の機械的整合性を検査。
  * 「物語的に面白いか」は判定しない。
  * LLM / Director / HUD / ActionPipeline 連携は未実施。
  * `pytest tests/test_action_proposal_validator.py -q`: 81 passed。

### 気づき

* A-F checks がすべて実装済みになった。
* validator はまだ実行系に接続していないため、Shadow mode の入口として安全に育てられる。
* 次にいきなりHUDやActionPipelineへつなぐより、まず `ValidationReport` と reason文言の contract を固定した方がよい。
* `config.yml` の HUD_DEBUG off は別件変更。必要なら別コミットで扱う。

### 次回の最初の一手

* Action Proposal DSL validator の contract を固める。

  * 公開APIとしての `validate_proposal()` 引数を確認する。
  * `ValidationReport.checks` / `ValidationReport.reasons` / `overall` の形式を固定する。
  * reason文言がテストで依存してよいものか、またはコード化された reason code を追加するか検討する。
  * まだ HUD / ActionPipeline / Director には接続しない。


## 2026-06-08（Session 34: Action Proposal DSL Check B/C）

### 今日やったこと（結果）

* Action Proposal DSL v0.1 の Check B: Uniqueness を実装。

  * `validate_proposal(..., active_action_ids=None)` に拡張。
  * `active_action_ids` 未指定なら `B_uniqueness = UNKNOWN`。
  * proposal id が既存 action id と重複する場合は `REJECT`。
  * 重複しない場合は `PASS`。
* Action Proposal DSL v0.1 の Check C: Requirements を実装。

  * `validate_proposal(..., known_requirement_keys=None)` に拡張。
  * `requirements` 未指定 / `None` / `{}` は `PASS`。
  * `requirements` が dict 以外なら `REJECT`。
  * `known_requirement_keys` 未指定なら `UNKNOWN`。
  * 未知の requirements key があれば `REJECT`。
  * 全 key が既知なら `PASS`。
* `pytest tests/test_action_proposal_validator.py -q` が成功。

  * 結果: `26 passed`

### 気づき

* Action Proposal DSL は、いきなり実行系に接続せず、A-F の検問を小さく固める方針が安全。
* B/C は外部情報を任意引数で渡す形にしたため、既存呼び出しを壊さず段階的に導入できる。
* C はまだ `RequirementsChecker` には接続していない。現段階では「requirements key の語彙チェック」に留めている。

### 次回の最初の一手

* Check D: Effects を小さく実装する。

  * まずは effects の構造だけを見る。
  * world state への実接続や ActionPipeline 連携はまだ行わない。
  * `effects` 未指定なら PASS、構造不正なら REJECT、検査材料不足なら UNKNOWN、という粒度で進める。



## 2026-06-07（Codex CLI trial）

### 今日やったこと（結果）

* OpenAI Codex CLI を Windows PowerShell から導入し、`codex/read-only-survey` ブランチで読み取り専用調査を実施。
* Codex に `STATE.md` / `LOGBOOK.md` / Action Proposal DSL 関連を確認させ、最初に触る低リスクタスクとして validator テスト追加を選定。
* `tests/test_action_proposal_validator.py` を追加。

  * valid proposal の `A_syntax == PASS`
  * required field 欠落、id形式不正、time_min不正の REJECT
  * B-F checks が現状 UNKNOWN
  * valid proposal でも B-F UNKNOWN のため overall UNKNOWN
* `pytest tests/test_action_proposal_validator.py -q` が成功。

### 気づき

* Action Proposal DSL は「アクション提案アクション」のための規約書・検問所に近い。
* まず現状仕様をテストで固定してから、B-Fを1つずつ実装する方が安全。
* Codex は初回から中枢ファイルを触らせず、テスト追加やvalidatorなど低リスク箇所に限定すると扱いやすい。

### 次回の最初の一手

* `Check B: Uniqueness` だけを小さく実装する。

  * `active_action_ids` が未指定なら B は UNKNOWN 維持。
  * 指定ありで proposal id が重複したら REJECT。
  * 重複なしなら PASS。



## 2026-04-02（Session 33）
### 今日やったこと（結果）
- **Obj1: Pack Single Source of Truth**
  - `cop_trickster_goals.yml` を削除し、`packs/cop_trickster.yml` に統一
  - `registry.py` に `extract_goals_from_pack()` 追加、`synthesize_from_text()` も経由するよう修正
  - `simulation.py` Path B を pack_data 経由に変更
  - 6テストファイルの goals ロードを pack 経由に移行
  - `pytest.ini` の `python_files` を `test_*.py` に修正（全テスト発見できるように）
- **Obj4: check_tip 二重源泉の解消**
  - `or_check_tip` (opportunity) と `dr_unread_tip` (discovery) を削除
  - check_tip は Director micro task (FREEZE) としてのみ残す
  - discovery_rules: 5→4件、opportunity_rules: 6→5件
- **Obj2: Recommended governance 修正**
  - `refresh_hud()`: affordance bridge 完了後に rec_action が governed & 非visible なら Recommended を抑制
  - `on_action_select("__recommended__")`: hud_cached_actions の visible_ids と照合して非表示なら skip
- **Obj3: Action Proposal DSL v0.1（種まき）**
  - `docs/action_proposal_dsl_v0.1.md`: 仕様書（proposal format、check A-F、三値結果、採用段階）
  - `src/action_proposal/validator.py`: `validate_syntax()` (Check A) 実装、B-F は UNKNOWN stub

### 確認できたこと
- 全12テスト（6ファイル）がパス。既存の壊れテスト3件は Session 33 以前のもの
- `extract_goals_from_pack()` が modes + affordances を正しく抽出
- `validate_proposal()` が syntax PASS / REJECT を正しく返す

### 次回の最初の一手（15分でやる）
- `python -m src.simulation` を HUD_DEBUG=1 で起動し、affordances loaded のカウントが discovery_rules=4, opportunity_rules=5 であることを確認

---

## 2026-03-30（Session 32）
### 今日やったこと（結果）
- **Affordance Bridge v2**: discovery / opportunity / label の3層分離を実装
  - `affordance_bridge.py` 全面書き換え: `evaluate_discoveries`, `inject_discovery`, `evaluate_opportunities`, `mark_opportunity_spent`, `merge_with_director_actions`, `apply_label_overrides`
  - discovery_rules 5件（trigger_type: passive_or_time / action_result / director_inject）
  - opportunity_rules 6件（visible_when でロケーション・モード制約）
  - label_rules 2件（rest の場所別ラベル差し替え）
- **goals / pack 参照ずれ修正**: `director.affordance_rules()` は `cop_trickster_goals.yml` を参照するが、v2 affordances を `packs/cop_trickster.yml` に書いていたことが発覚。goals 側に移設
- **canonical_facts**: `cop_trickster_goals.yml` の `affordances.canonical_facts` に5件のフラグを定義、`synthesize_world()` で `world["flags"]` に読み込み
- **governed action 導入**: opportunity_rules を持つ action_id は、visible opportunity がないとき Director 既定候補からも抑制される
  - `merge_with_director_actions()` に `governed_action_ids` 引数追加
  - collect_fiber / fix_cam_clock が discovery + crime_scene + PURSUE のときだけ表示されることを確認
- **HUD_DEBUG 拡張**: discovery 注入 Combobox + Inject ボタン、startup affordance summary ログ、注入後の discovery/spent/opportunity 状態ログ
- **spent 管理**: discovery は残り続け、opportunity 側（action_id ベース）で spent を管理
- **カスタム YAML パーサ対応**: label_rules の `label` が `match` dict 内に吸い込まれる問題を fallback で対処

### 確認できたこと
- passive_or_time (unread_tip): 初回 action 実行で自動 discovery 発火
- action_result (blue_fiber / cam_clock_skew): action_id 一致で発火
- director_inject: `inject_discovery()` による外部注入のみ（evaluate 内では不発火）
- visible_when: location / mode 制約が正しくフィルタ（crime_scene → apartment で消失）
- spent: 実行済み opportunity が HUD から消える
- merge dedup + governed: Director 候補と opportunity の action_id 重複排除、governed 抑制
- label_rules: rest のラベルが location で切り替わる

### まだ曖昧な点
- **★Recommended が governed 未対応**: Recommended ボタンが affordance の visible_when を無視して出る・実行できる可能性あり
- **check_tip の二重源泉**: Director FREEZE micro task と affordance opportunity の両方に存在。governed で抑制されるが、設計意図が曖昧
- **goals / pack 二重管理**: cop_trickster_goals.yml（Director 用）と packs/cop_trickster.yml（pack メタデータ）に重複構造がある。single source of truth 化が必要
- **action_result trigger の実動作未確認**: examine_scene / review_footage が action_definitions に未定義
- **move_low_profile の移動先決定ロジック**: 未実装

### 次回の最初の一手（15分でやる）
- `★Recommended` が governed action の visible_when を尊重しているか確認。`hud_callbacks.py` の `recommended_action()` 呼び出しフローを追う

---

## 2026-03-29（Session 31）
### 今日やったこと（結果）
- **HUD location表示**: `director_hud.py` に location 行を追加
  - 通常モード: 読み取り専用ラベル `📍 拠点_安アパート`
  - デバッグモード (`HUD_DEBUG=1`): `ttk.Combobox` dropdown（4箇所選択可）
- **hud_callbacks.py**: `refresh_hud()` で `game_state["current_location"]` を HUD に反映
  - debug dropdown 変更時: `game_state` 更新 → `bump_hud_cache_rev()` → `refresh_hud()` → affordance label_rules 再評価
- **simulation.py**: Session 30 の一時上書き `_game_state["current_location"] = "情報源_夜の酒場"` を削除
  - `init_state.py` のパック定義 (`拠点_安アパート`) がデフォルトとして使われる
- **config.yml**: `debug.hud_debug` セクション追加（`is_hud_debug_enabled()` は既に対応済みだった）

### 発見（次にも効く）
- HUD dropdown で location を変えると label_rules が即座に再評価される → affordance の動作確認が容易
- PURSUE モードの既定 action と discovery 由来 action に重複がある（explore 系）
- 酒場やアパートにいても現場系 action（collect_fiber 等）が見える → 場所による可視条件が必要
- discovery は「手がかり」なのか「action 候補」なのか、現状の設計では曖昧

### 次回の最初の一手（15分でやる）
- `cop_trickster.yml` の affordances セクションを眺めて、discovery と opportunity の分離案をスケッチする

---

## 2026-03-29（Session 30）
### 今日やったこと（結果）
- **Affordance Bridge** (`src/affordance_bridge.py`) 新規作成
  - `evaluate_discoveries()`: アクション実行後にtrigger条件マッチ→discoveries追加
  - `get_pending_discoveries()`: HUD用、未消費のdiscoveryをリスト返却
  - `apply_label_overrides()`: label_rulesに基づきアクションラベルを文脈差し替え
  - `consume_discovery()`: discovery由来アクション実行時に消費済みマーク
- **cop_trickster.yml** に `affordances:` セクション追加
  - discovery_rules: explore@事件現場→collect_fiber出現、explore汎用→check_tip出現
  - label_rules: rest@FREEZE+酒場→「酒場から家に帰る」、rest@FREEZE+アパート→「仮眠をとる」
- **director.py**: `synthesize_world()` にaffordances初期化追加、`affordance_rules()` メソッド追加
- **action_pipeline.py**: `request_action()` にdiscovery評価 & 消費フック追加
- **hud_callbacks.py**: `refresh_hud()` にdiscoveryマージ & ラベル上書き追加

### 発見（次にも効く）
- プロジェクトのカスタムYAMLパーサー (`yaml/__init__.py`) は flow mapping `{key: value}` をサポートしない → block style で書く必要あり
- affordance_bridge は Director / pack YAML に依存しない純粋関数群なのでテストしやすい

### 次回の最初の一手（15分でやる）
- `python -m src.simulation` で起動→探索実行→HUDに「現場で青い繊維を採取」が出現するか目視確認

---

- [ICEBOX] GM-AI世界を用いた人工エージェントの自己連続性 C(t) 研究構想。詳細は `\general_documents\future_goals\RESEARCH_NOTES.md` を参照。