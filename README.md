## これは？
ゲームマスターAIです。
AIと人間が協調してゲーム作りをするシステムを目指しています。


## 環境構築

```bash
git clone https://github.com/user242-0/hybrid_gm_ai.git
cd hybrid_gm_ai
cp .env.example .env      # ↑自分の API キーを記入
pip install -e .
python -m src.simulation
