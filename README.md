## ゲームマスターAI
AI(OPENAI ChatGPT)と人間が協調してゲーム作りをするAI作りを目指しています。
詳しくはgeneral_documents/gm_ai_definition.md
随時更新中。

## 環境構築

```bash
git clone https://github.com/user242-0/hybrid_gm_ai.git
cd hybrid_gm_ai
cp .env.example .env      # ↑自分の API キーを記入
pip install -e .
python -m src.simulation
