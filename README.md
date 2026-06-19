# Game Master AI (hybrid_gm_ai)

## What this is

Director 層、RC_AI、ActionSpec を組み合わせ、シナリオ pack、MicroGoal、Scene injection、Emotion (RGB) を扱うシミュレーション実験プロジェクトです。

## Quick start

### Install

```console
pip install -e ".[dev]"
```

### Run

```console
python -m src.simulation
```

通常はメイン GUI と Director HUD が起動します。前提テキストを指定する場合は次のように実行できます。

```console
python -m src.simulation --premise-text "..."
```

### Exit

メイン GUI の入力欄に `q` と入力し、Enter キーを押すと終了します。`quit` と `exit` も使用できます。

現行コードでは `USE_CLI = False` のため、通常起動は GUI 入力です。コード上で CLI モードを有効にした場合は、端末の `>>` プロンプトに同じ終了コマンドを入力します。

## Tests

```console
pytest -q
```

現在のテストは all green です。この環境での最新実行では skip はありません。Tkinter またはディスプレイを利用できない環境では、Director HUD のテスト 1 件が skip される場合があります。

## Implemented features

- Director HUD
- `cop_trickster` シナリオ pack
- RC / `switch_character`
- Action Proposal DSL v0.1 の検証
- Action Proposal の shadow log
- read-only の advisory feed / provider
- `actor_id` で表示対象を絞る AI 提案 HUD
- ActionSpec と ActionPipeline による requirements、時間、感情差分、effects、実行関数の処理

AI 提案 HUD 用のデモデータは次のコマンドで生成できます。

```console
python -m src.action_proposal.demo_seed
```

shadow log の標準出力先は次のとおりです。

```text
jobs/%Y%m%d_quick/action_proposal_shadow.jsonl
```

## Current limitations

- AI 提案 HUD は現時点では read-only 表示です。
- AI 提案はまだ `ActionPipeline` や Director HUD の `Actions` listbox には接続していません。
- advisory feed/provider は shadow log の PASS レコードを読み取り、現在の `actor_id` に合う提案を表示する用途に限定されています。

## Key concepts

- Director: pack を基に micro-goal を選定し、シーンを注入します。
- RC_AI: mode、emotion、action deltas を用いて行動を選択します。
- Emotion: `(R, G, B) = (衝動, 自己制御, 優しさ)` です。
- ActionSpec: legacy/new action 定義を統一し、effects で world を更新します。
- Packs: `data/director/packs/*.yml` に modes、goals、actions、world defaults を定義します。

## Directory layout

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
