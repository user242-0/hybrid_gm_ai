## ゲームマスターAI

AI（主にOpenAI ChatGPT）と人間が協調してゲーム作りをするAI、それが「ゲームマスターAI」です。  
このプロジェクトは、AIがプレイヤーの行動ログを解析し、動的にルールを提案・実装する「進化するゲームシステム」を目指します。

詳しくは [`general_documents/gm_ai_definition.md`](general_documents/gm_ai_definition.md) を参照してください。  
このファイルには、ゲームマスターAIの定義、目的、AIと人間の役割分担などの基本設計思想が記載されています。

---

## フォルダ構成（概要）

```
hybrid_gm_ai/
├── general_documents/       # ゲームマスターAIの定義や構想メモなど
├── src/                     # Pythonによる実装コード群
│   ├── simulation.py        # 実行エントリーポイント
│   └── ...                  # 各種モジュール
├── data/                    # プレイヤーのログやルールデータなど
├── .env.example             # APIキーなどの環境変数テンプレート
└── README.md                # 本ファイル
```

---

## 環境構築

以下の手順でセットアップできます：

```bash
git clone https://github.com/user242-0/hybrid_gm_ai.git
cd hybrid_gm_ai
cp .env.example .env      # 自分のAPIキーを.envに記入
pip install -e .
python -m src.simulation
```

---

## 使い方（例）

初期状態では、**シンプルなテキストベースのアドベンチャーゲーム**が動作します。
プレイヤーの行動に応じて、AIが状況描写やNPCの反応を返します。

```bash
python -m src.simulation
```

---

## 編集ポイント（今後の開発方針）

### ① シミュレーションの充実

* 色に意味を持たせる：戦闘関連の「赤」、静寂や内省の「青」、システムの正常動作「緑」など。
* イメージはピクセル単位で視覚化されることを想定。
* NPC ↔ プレイヤー間の切り替え、関係性定義、およびリアルタイム行動の制御を検討中。

### ② AIによるルール提案～実装の自動化

+ * プレイログは `data/logs/*.jsonl` に保存されます（※ `.jsonl` = JSON Lines）。
+ * **現在はルール自動生成ロジックは未着手**。  
+   将来的に `scripts/generate_rules.py` でログ → `rules_draft.jsonl` を生成 →  
+   人間レビュー → `src/action_definitions.py` へ反映、というワークフローを予定しています。

---

今後の発展に向けて、**AIによるルール提案・実装の全自動化と、意味のある色／関係性の付与**を軸に進化させていきます。


## 💡 Emotion-Based Simulation: simulation_e.py

This version implements an emotion-driven action selection system.

- Each choice is assigned an RGB axis and intensity.
- The player's emotional color (心の色) affects which actions stand out.
- Visual feedback is provided via ANSI terminal coloring.

⚠️ Note:
Currently, simulation_e.py defaults to auto-selecting "green" actions.
This is a placeholder behavior and not yet dynamically controlled.

### Run emotion-based version:

```bash
python -m src.simulation_e
```
---
### Quit / Exit
ゲーム中いつでも `q`, `quit`, `exit` を入力 (または `Ctrl-C`) すると、安全にシャットダウンします。
