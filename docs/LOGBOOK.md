# LOGBOOK.md - 開発日誌（雑談OK）

ルール:
- 1エントリは短くていい（箇条書きでもOK）
- 「気持ち」+「技術メモ」+「次回の最初の一手」を1つ入れると最強
- 長文になったら、`general_documents/diary/` に退避してリンクを貼る

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

## 2026-03-28（Session 29）
### 気分 / 雑談
- バグ修正セッション。初期化漏れと設定ミスの組み合わせで2つの機能が死んでいた。

### 今日やったこと（結果）
- **Bug Fix 1**: 「戦う」「戦わない」「ただ、受け入れる」がGUI選択肢に出なかった
  - 原因: `init_state.py` で `has_enemy` / `enemy` を設定していなかった
  - 修正: `init_game_state()` に `has_enemy: True`, `enemy: antagonist` を追加
  - `engage_combat`/`avoid_combat`/`accept_attack` の requirements `{"has_enemy": True}` がパスするようになった
- **Bug Fix 2**: RO金色ラベルが常に空だった
  - 原因: `config.yml` で `ro.enabled: false` のままだった → `recommend()` が即座に None を返していた
  - 修正: `ro.enabled: true` に変更
  - `hud_callbacks.py` の `refresh_hud()` のRO表示コード自体は正しかった（Session28で実装済み）

### テスト
- `pytest -q`: 全5テスト通過
- `init_game_state()` → `has_enemy: True`, `enemy.name: 愉快犯` 確認
- `RequirementsChecker.check_all({"has_enemy": True})` → True
- `get_available_choices()` で engage_combat / avoid_combat / accept_attack が出現
- `ro.recommend()` が dict を返すことを確認

### 発見（次にも効く）
- `init_state.py` が game_state の初期構造を決めるが、アクション要件（requirements_checker）との整合を忘れやすい
- config.yml の `enabled: false` が silent に機能を殺す（except pass パターンと合わさると発見が遅れる）

### 次回の最初の一手（15分でやる）
- 実際に simulation を起動して「戦う」選択 + RO金色ラベル表示を目視確認

---

## 2026-03-26（Session 28）
### 気分 / 雑談
- Session 27 で独立モジュールとして作った resolve_exchange が、ようやく実際の戦闘に接続された。CSVを足すだけで武器バリエーションが増える設計が効いている。

### 今日やったこと（結果）
- **Task 1**: `resolve_exchange` を `engage_combat` に統合
  - `_determine_outcome(attack_power)` ヘルパー追加（hit_chance = 0.25〜0.75、攻撃力で微調整）
  - 戦闘ループを改修: 攻撃側・防御側それぞれ outcome→resolve_exchange→narrative→HP処理
  - `game_state["combat_narrative"]` にテキスト蓄積
  - 既存の戻り値（"勝利"/"敗北"）・HP書き戻しはそのまま維持
- **Task 2**: `data/combat/unarmed_log_dictionary.csv` 新規作成
  - 22エントリ: miss(evade4+guard4+deflect4+clinch4=16) + hit(chip2+counter2+seize2=6)
  - `attacker_weapon=unarmed`, `range=near`
  - cop↔trickster の組み合わせ、UTF-8 BOM (`utf-8-sig`)
  - `log_dict.py` が `data/combat/*.csv` を glob するのでコード変更不要
- **Task 3**: RO Phase B — HUD に RO 助言表示
  - `director_hud.py`: `ro_var` (StringVar) + `row_ro` (金色ラベル `#FFD700`) + `set_ro_recommendation()` メソッド追加
  - `hud_callbacks.py`: `refresh_hud()` 末尾で `game_state["ro_recommendation"]` を読み取り HUD に表示
  - ウィンドウサイズ: `520x360` → `520x390`, minsize `320` → `350`

### テスト
- `pytest -q`: 全5テスト通過
- `_determine_outcome()` の import + 動作確認OK
- `pick_combat_log(range_="near", attacker_weapon="unarmed", ...)` で正しくCSVからテキスト取得
- `DirectorHUD` import + `set_ro_recommendation` メソッド存在確認OK

### 発見（次にも効く）
- `_determine_outcome` の hit_chance クランプ (0.25-0.75) で、戦闘が長すぎ/短すぎになるのを防げる
- dict型の敵は `gs["party"]` に居ないため resolve_exchange の narrative が空文字になるが、ダメージ処理は正常動作する（設計通り）

### 次回の最初の一手（15分でやる）
- `ro.enabled: true` で実際にシミュレーションを回して、HUDのRO助言表示を目視確認する

---

