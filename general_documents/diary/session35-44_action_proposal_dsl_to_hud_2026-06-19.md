# Session 35-44: Action Proposal DSL to HUD

Archived from `docs/LOGBOOK.md` on 2026-06-19.

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
  * `jobs/` は完全な一時ゴミ箱ではなく、一部はプレイセッション監査ログとして扱う必要が出てきた

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
  * HUD側がshadow logの場所を知らなくても、providerからitemsを取得できるようにした
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
* 当時の `pytest -q` は既存と思われる3件で失敗。

  * `tests/test_npc_switch.py::test_npc_switch`
  * `tests/test_requirements_time_weather.py::test_statue_actions_are_gated_by_time_and_weather`
  * `tests/test_scene_graph_roundtrip.py::test_scene_graph_roundtrip_minimal`
* `python -m src.simulation` でHUD起動を確認。
* 手動で作成した `action_proposal_shadow.jsonl` から、HUDの「AI提案」欄に提案が表示された。
* PowerShellで作成した初回サンプルの文字化けは実装バグではなく、テストデータ作成時の文字コード問題だった。

### 気づき

* Action Proposal DSLは「提案→検問→ログ→HUD表示」まで到達した。
* ただし、提案を生成する主体は本体に接続されていなかった。
* AI提案欄はshadow logにPASS済みrecordがある場合だけ表示される。
* 実行可能化より先に、デモ用proposal生成・保存導線を作る方針とした。
* `jobs/%Y%m%d_quick/` の監査ログは保持対象として扱う必要がある。

### 次回の最初の一手

* Action Proposal Demo Producer / Seed を作る。
* proposalをA-F validatorに通し、shadow logへ保存してHUD表示を確認する。
* ActionPipelineやActions listboxにはまだ接続しない。

## 2026-06-14（Session 35-37: Action Proposal DSL Check D/E/F）

### 今日やったこと（結果）

* Check D: Effects を実装。

  * `validate_proposal(..., known_effect_paths=None)` に拡張。
  * dict/list形式の effects を検査。
  * list形式では各 item の `op` / `path` 構造を検査。
  * `op` は `add` / `set` のみ許可。
  * world stateへの適用やregistry/pipeline連携は未実施。
  * `pytest tests/test_action_proposal_validator.py -q`: 45 passed。

* Check E: Safety を実装。

  * `validate_proposal(..., safety_limits=None)` に拡張。
  * `forbidden_effect_paths` による禁止path検査を追加。
  * `max_abs_delta` / `max_abs_delta_by_path` によるadd delta上限検査を追加。
  * `set` はdelta上限対象外。
  * 判定不能なadd valueはUNKNOWN。
  * `pytest tests/test_action_proposal_validator.py -q`: 62 passed。

* Check F: Narrative を実装。

  * `validate_proposal(..., narrative_context=None)` に拡張。
  * source / rationale / modes / allowed_modes / tone_tags / tags / forbidden_tags の機械的整合性を検査。
  * 「物語的に面白いか」は判定しない。
  * LLM / Director / HUD / ActionPipeline連携は未実施。
  * `pytest tests/test_action_proposal_validator.py -q`: 81 passed。

### 気づき

* A-F checksがすべて実装済みになった。
* validatorはまだ実行系に接続していないため、Shadow modeの入口として安全に育てられる。
* 次はHUDやActionPipelineへの接続より、`ValidationReport` とreason文言のcontract固定を優先する方針とした。

### 次回の最初の一手

* `validate_proposal()` の公開APIと、`ValidationReport.checks` / `reasons` / `overall` の形式を固定する。
* reason文言への依存を避けるため、reason code追加を検討する。
