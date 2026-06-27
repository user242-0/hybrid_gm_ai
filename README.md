# Game Master AI (hybrid_gm_ai)

> **English summary:** GM-AI is an experimental narrative game simulation engine.
> This repository is a **technical prototype**, not a finished game.
> Prototype Demo #1 focuses on `switch_character`: changing the controlled character changes the meaning of the same world, HUD goals, and action vocabulary.

## これは何か / What this is

Game Master AI / GM-AI は、AI支援によるナラティブゲームシミュレーションエンジンの技術実証プロジェクトです。

長期的には、AIがルール、イベント、行動候補、物語上の変化を提案し、人間のプレイヤーや制作者がそれを採用・調整することで、ゲームシステムやシナリオが少しずつ変化していく体験を目指しています。

ただし、このリポジトリは現時点では**完成ゲームではありません**。
現在は、GM-AIの中核になりうる仕組みを段階的に検証している **technical prototype / 技術実証** です。

このプロジェクトは、開発過程を公開するためのタイムスタンプであり、ポートフォリオ記録でもあります。

## Prototype Demo #1 / プロトタイプデモ #1

**Title:** GM-AI Prototype Demo #1
**Scenario:** 落魄の刑事 vs 愉快犯
**Focus:** `switch_character`

今回の60秒デモでは、「落魄の刑事が愉快犯を追う」という小さなシナリオを使っています。

このデモで見せたい中心コンセプトは、`switch_character` です。

GM-AIでは、敵役を単なる静的なターゲットとしてだけ扱うのではなく、同じ世界内に存在するキャラクターとして扱います。
操作キャラクターを刑事から愉快犯へ切り替えると、同じ事件であっても、見える目的、行動語彙、HUD上の意味が変わります。

In this demo, the enemy is not only a static target.
The trickster is also represented as a character in the same world.
By switching the controlled character, the same incident is interpreted through a different role.

## 今回のデモで実証していること / What this demo demonstrates

このデモは、完成したゲームループを見せるものではありません。
今回の目的は、**操作キャラクターを切り替えることで、同じ世界の意味と行動語彙が変わる**ことを示すことです。

具体的には、以下を実証しています。

* 操作キャラクターを「刑事」と「愉快犯」の間で切り替えられる
* 同じ事件でも、誰を操作しているかによって意味が変わる
* 刑事視点では、HUDの語彙が以下に寄る

  * 証拠
  * 証言
  * 追跡
* 愉快犯視点では、HUDの語彙が以下に寄る

  * 逃走
  * 撹乱
  * 潜伏
* Director HUD の表示が、現在操作中のキャラクターに応じて変わる

  * MicroGoal
  * Actions
  * 提案候補
* 提案候補は、以下の流れで read-only 表示される

  * Action Proposal DSL
  * A-F validation checks
  * Shadow Log
  * Advisory Feed / Provider
  * HUD read-only display

現時点では、提案候補は表示のみです。
HUD上の提案候補をクリックして採用・実行する導線は、まだ未実装です。

## Quick start / 起動方法

### Install

```console
pip install -e ".[dev]"
```

### Generate demo advisory proposals / デモ用提案候補を生成する

現在のYouTubeデモと同じ提案候補を表示したい場合は、先に次のコマンドを実行します。

```console
python -m src.action_proposal.demo_seed
```

このコマンドは、刑事向け・愉快犯向けのデモ用 Action Proposal shadow record を生成します。

* 刑事向け: 「証言時刻を照合する」
* 愉快犯向け: 「偽の痕跡を残す」

### Run

```console
python -m src.simulation
```

通常は、メインGUIと Director HUD が起動します。

前提テキストを指定する場合は、次のように実行できます。

```console
python -m src.simulation --premise-text "..."
```

## How to quit / 終了方法

メインGUI下部の入力欄に次を入力し、Enter キーを押すと終了します。

```text
q
```

`quit` と `exit` も使用できます。

注意: `q` を入力するのは Director HUD ではなく、テキストログと入力欄があるメインGUI側です。

## Tests / テスト

```console
pytest -q
```

## Implemented features shown in this prototype / 現在デモで見せている実装

このプロトタイプで、今回のデモに関係する主な実装は以下です。

* Director HUD
* `cop_trickster` シナリオ pack
* RC / `switch_character`
* 操作キャラクターに応じたHUD表示
* 操作キャラクターに応じた MicroGoal 表示
* 操作キャラクターに応じた Actions list
* Action Proposal DSL v0.1
* A-F proposal validation checks
* proposal record 用の Shadow Log
* read-only Advisory Feed / Provider
* HUD上の read-only 提案候補表示
* actor-targeted demo proposal seed

  * Detective / 刑事: 「証言時刻を照合する」
  * Trickster / 愉快犯: 「偽の痕跡を残す」

## Current limitations / 現時点の制限

このリポジトリは、現時点では technical prototype / 技術実証です。

現在の主な制限は以下です。

* 完成ゲームではありません
* 現在のシナリオコンテンツは、システム概念を示すための小さなデモです
* 提案候補は現時点では read-only 表示です
* 提案候補はまだ HUD の Actions listbox には接続されていません
* 提案候補をHUDから直接採用・実行する導線は未実装です
* 現在のデモ提案候補は `python -m src.action_proposal.demo_seed` で生成します
* コンテンツ縦切りや本格的なゲーム体験は、まだ開発途中です
* UIはまだ開発者向けのプロトタイプHUDです
* 初見プレイヤー向けのチュートリアルやオンボーディングは未整備です

This is not a finished game.
The current demo focuses on one prototype concept: character switching changes how the same world is interpreted.

## Next planned work / 次に作る予定

近い開発目標は以下です。

* 「落魄の刑事 vs 愉快犯」シナリオのコンテンツ縦切りを強化する
* 場所、発見、状況変化によって表示アクションが変わる導線を整える
* A-F検問済みの Action Proposal を、安全に採用・実行する導線を作る
* 操作キャラクターごとの MicroGoal / Actions / 提案候補の分離を進める
* 公開デモ用の導線とドキュメントを、誇張せず分かりやすく整える

## Key concepts / 主要概念

* Director: pack を基に micro-goal を選定し、シーンを注入します。
* RC_AI: mode、emotion、action deltas を用いて行動を選択します。
* Emotion: `(R, G, B) = (衝動, 自己制御, 優しさ)` です。
* ActionSpec: legacy/new action 定義を統一し、effects で world を更新します。
* Action Proposal DSL: 外部エージェントやシステムが提案する行動候補を、A-F検問で検証するための形式です。
* Shadow Log: 提案候補をすぐ実行せず、検証結果をJSONLとして記録するためのログです。
* Advisory Feed / Provider: Shadow Log の PASS record を HUD 表示用の提案候補へ変換する read-only 層です。
* Packs: `data/director/packs/*.yml` に modes、goals、actions、world defaults を定義します。

## Directory layout / ディレクトリ構成

```text
src/
  action_proposal/
  director/
  ui/
  rc_ai.py
  action_model.py
  action_effects.py
  action_definitions.py
  action_registry.py
data/director/packs/
tests/
```
