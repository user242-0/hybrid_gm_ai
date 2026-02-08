# LOGBOOK.md - 開発日誌（雑談OK）

ルール:
- 1エントリは短くていい（箇条書きでもOK）
- 「気持ち」+「技術メモ」+「次回の最初の一手」を1つ入れると最強
- 長文になったら、`general_documents/diary/` に退避してリンクを貼る

---

## 2026-02-08（Session 27）
### 気分 / 雑談
- 戦闘にナラティブが付く第一歩。CSVにテキストを書いておけば、条件に合わせて引き当てられる仕組みができた。

### 今日やったこと（結果）
- **戦闘ログ辞書** (`src/combat/log_dict.py`) 新規作成
  - `data/combat/*.csv` を全読み込み（BOM対応、キャッシュ付き）
  - `pick_combat_log()`: range/weapon/outcome/subtype/role で4段階フォールバックマッチ
  - 完全一致 → role緩和 → subtype無視 → 両方緩和
- **resolve_exchange** (`src/combat/resolve_exchange.py`) 新規作成
  - CharacterStatus から weapon_type / role を自動取得
  - `pick_combat_log()` でテキスト引き当て → `gs["combat"]["log"]` / `last_exchange` に記録
  - role マッピング: `faction=="player"→"cop"`, `is_npc→"trickster"` (簡易、将来パックから引く)
- `src/combat/__init__.py` 作成（パッケージ化）
- 既存ファイルへの変更なし

### テスト
- 検証スクリプト: pick_combat_log 完全一致 / フォールバック(role緩和/subtype無視) / マッチなし→None
- resolve_exchange: gs["combat"]["log"]への追記、text取得を確認
- 全テスト通過

### 発見（次にも効く）
- CSV の BOM (`utf-8-sig`) を忘れると DictReader のヘッダ最初の列名に BOM が混入して条件一致しなくなる。
- フォールバックは `_match()` 内部で `subtype=None` / `role=None` で「条件スキップ」にするのがシンプル。
- tags列は key=value 形式の自由テキストでも十分実用的（構造化は将来必要になったら）。

### 次回の最初の一手（15分でやる）
- resolve_exchange を既存の combat アクション経路から呼ぶ統合ポイントを探る（src/actions/combat.py を読む）。

---

## 2026-02-07（Session 26）
### 気分 / 雑談
- RO（Reversible Operator）の最初の一歩。まだ助言を出すだけだが、ログ識別子の整備から入ったので基盤は堅い。
- 「誰が決めたか」をログに残す仕組みが入ったことで、将来の分析がずっと楽になるはず。

### 今日やったこと（結果）
- **Task26-0**: ログ識別子の最小改修
  - `logger.py` の `log_action()` に `controller_id` / `actor_rc_id` 自動付与ロジックを追加
  - RC_AI → `controller_id="RC_AI:刑事"`, GUI → `controller_id="PLAYER:GUI"` など
  - `actor_rc_id` = `actor_id` のコピー（将来の表示名分離に備える）
  - レガシー呼び出し（`actor` フィールド）にもfallback対応
  - 呼び出し側が明示的に `controller_id` を渡せば上書きしない（RO予約対応）
- **Task26-1 (Phase A)**: RO雛形（助言＋理由）
  - `src/ro/ro.py` 新規作成: `recommend()` がplayerログ直近N行を読みスコアリング
  - スコアリング: microgoal近接(+2.0) / 連打抑制(-2.0/-1.0) / 頻度ペナルティ
  - 出力: `action_id` + `why`（必須）+ `risk` / `plan_b`（任意）
  - `config.yml` に `ro.enabled: false` / `ro.log_window: 50` 追加
  - `action_pipeline.py`: playerアクション後に自動呼び出し、`game_state["ro_recommendation"]` に格納
  - RO日誌: `data/logs/ro_diary_latest.jsonl` に `controller_id="RO:<actor>"` 形式で出力

コミット:
- c72773e: Feat: auto-inject controller_id and actor_rc_id into all JSONL log lines
- 4d728c2: Feat: add RO (Reversible Operator) Phase A – advice from player log

### テスト
- `tests/test_logger_ids.py`: 6ケース（RC_AI/GUI/HUD、レガシーfallback、明示値保持、空入力）
- `tests/test_ro.py`: 7ケース（無効時None、microgoalブースト、連打抑制、diary出力、空候補、plan_b、空ログ）
- 既存テスト（test_director.py）含め全18テスト通過

### 発見（次にも効く）
- ログの一元化ポイント（`log_action`）に自動付与を入れると、呼び出し側の変更ゼロで全行に反映できる。
- ROは `try/except` でラップして「ROの障害がゲームプレイを止めない」を保証する設計が大事。
- `_ro_cfg()` を分離しておくとテストのmockが楽。

### 次回の最初の一手（15分でやる）
- `config.yml` の `ro.enabled: true` にして起動 → GUIでアクション実行 → `data/logs/ro_diary_latest.jsonl` にdiaryが書かれることを確認。
