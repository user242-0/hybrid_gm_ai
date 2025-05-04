## ゲームマスターAI
AI(主にOpenAI ChatGPT)と人間が協調してゲーム作りをするAIを一緒に作りましょう。
詳しくはgeneral_documents/gm_ai_definition.mdにて。
`general_documents/gm_ai_definition.md` には、「ゲームマスターAIとは何か」「このプロジェクトの目指すもの」「AIと人間の役割分担」などの基本的な設計思想や用語定義が記載されています。


## フォルダ構成（概要）
hybrid_gm_ai/
├── general_documents/ # ゲームマスターAIの定義や構想メモなど
├── src/ # Pythonによる実装コード群
│ ├── simulation.py # 実行エントリーポイント
│ └── ... # 各種モジュール
├── data/ # プレイヤーのログやルールデータなど
├── .env.example # APIキーなどの環境変数テンプレート
└── README.md # 本ファイル

## 環境構築

```bash
git clone https://github.com/user242-0/hybrid_gm_ai.git
cd hybrid_gm_ai
cp .env.example .env      # ↑自分の API キーを記入
pip install -e .
python -m src.simulation

## 使い方（例）

初期状態では、シンプルなテキストベースのアドベンチャーゲームが動作します。
以下のコマンドで開始：

```bash
python -m src.simulation
