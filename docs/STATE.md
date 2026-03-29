# STATE.md - 現在地（最優先で更新）

> このファイルは「数週間空いても復帰できる」ための現在地メモ。
> Claude Code / Cursor / 人間が、最初に読む。


## 0. いま何を作ってる？
- プロジェクト: hybrid_gm_ai（ナラティブゲームシミュレーションエンジン）
- 直近の方向性: ネオノワール「落魄の刑事 vs 愉快犯」シナリオを軸に、会話アクションを実装して"遊べる体験"を強化

- RO（Reversible Operator）：プレイヤー側の常駐オペレーター層。ログ編集→方針（優先度/制約/評価）パッチ→RC_AI誘導を担う。
  - Reversibleとは、以下の立場・役割の可逆性を指す。
  - 1.指し手の可逆性（Human↔RO）
    - 通常は RO→RC が自然だが、状況によって プレイヤーがROから指示を受けて動く（RO→プレイヤー→RC）順も成立する。
  - 2.視点・没入の可逆性（メタ観察↔物語没入）
    - プレイヤーがメタ観察（ログ収集／優先度決定／状況把握）を行うモード
    - ROが感情・物語に没入し、RC_AI寄りの機能（局所判断）を担うモード
    - → 普段と逆が成立する＝Reversible
  - 3.ルール提案・承認の可逆性（提案者↔承認者）
    - ルール提案→承認のような特殊アクションにおいて、立場を逆にできる（RO提案／人間承認 ⇄ 人間提案／RO承認）。
  - 4.コーチングの可逆性（助言者↔育成対象）
    - 通常はROがアドバイスを与える側だが、人間がROをコーチングし育成することもある。

## 1. すぐ動かす（入口コマンド）
- Run:
  - `python -m src.simulation`
- Test:
  - `pytest -q`  （※まだ無い/別コマンドならここを更新）
- RC（回帰/自動挙動）:
  - （例）`python -m src.simulation --rc` / `python -m src.rc_ai` など
  - 現状のRC起動方法: TODO（確定したらここに1行で）

## 2. いまの状態（3行で）
- ✅ 動くもの:
  - `python -m src.simulation` で起動し、HUDから選択→ActionPipeline経由でアクション実行できる
  - 初期stateが `cop_trickster` パック準拠（刑事/愉快犯・ロケーション・関係性タグ）で立ち上がる
  - **emotions_by_actor** でactor別emotion管理、set_emotion/switch_character後も値が保持される
  - 全JSONLログに `controller_id`（意思決定者）/ `actor_rc_id`（行動主体）が自動付与される
  - **RO (Reversible Operator)** Phase A+B 導入済み（助言生成 + HUD黄色テキスト表示）
  - **戦闘ログ辞書** + **resolve_exchange** が `engage_combat` に統合済み（hit/miss判定 → narrative描写 → HP処理）
  - 戦闘CSV: knife + unarmed の2武器種をサポート
  - **Affordance Bridge** 導入済み（GUIアクション結果→HUD候補追加/ラベル差し替えの汎用ブリッジ）
- ⚠️ いまの課題:
  - ROがRC_AIの行動選択に影響を与える仕組み（policy_patch）が未実装
  - 会話テンプレがまだ少なく、状況（場所/時間/天候）と関係性の掛け算が薄い
  - RC_AIの「緑優先」をキャラの心値×アクション心値による閾値フィルタに発展させる必要あり
- 🎯 今やっている目的:
  - Affordance Bridgeで「探索→発見→HUD候補追加」「文脈ラベル変化」をデータ駆動で実現
  - RO層を導入し、プレイヤー↔RO↔RC_AIの「可逆的な指し手」の基盤を作る

## 3. 直近の変更（最新3つだけ）
- 2026-03-29: Session30: Affordance Bridge実装 — GUIアクション結果→HUD候補/ラベル変化の汎用ブリッジ
- 2026-03-28: Session29: init_stateにhas_enemy/enemy追加（戦闘アクション表示修正） + ro.enabled: true（RO金色ラベル修正）
- 2026-03-26: Session28: resolve_exchange を engage_combat に統合 + unarmed CSV追加 + RO Phase B (HUD助言表示)

## 4. 次にやること（最大3つ・小さく）
1. RO Phase C: ROがpolicy_patchを出し、RC_AIの行動選択に影響を与える仕組み
2. RC_AIの「緑優先」をキャラの心値×アクション心値による閾値フィルタに発展させる
3. talkテンプレを状況（場所/時間/天候）にも反応させて増やす

## 5. ブロッカー（止まってる理由があれば）
（現状）大きなブロッカーなし。Affordance Bridge実装済み。実動確認推奨。

## 6. 参考（読む順番）
1. `CLAUDE.md`（前提とルール）
2. `docs/STATE.md`（このファイル）
3. `docs/LOGBOOK.md`（日誌・気づき）
4. 主要ファイル:
   - `src/simulation.py`
   - `src/game_context.py`
   - `src/ui/action_pipeline.py`
   - `src/ui/hud_callbacks.py`
   - `src/director/director.py`
   - `src/affordance_bridge.py`

## 7. 作業ブランチ / バックアップ
- 基準（安定）: `cursor-trial/microgoal-logging`
- 作業（Session30）: `feature/session30-affordance-bridge`
- 作業（Session29）: `feature/session27-engagement-fight`（Session28-29もこのブランチで継続）
- バックアップ: `backup/pre-session26-20260207`, `backup/pre-session25-20260203`
