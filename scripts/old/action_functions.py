import time
from logger import log_action  # ログ関数をインポートする例
import random 
import openai
import os
from dotenv import load_dotenv
import json

# .envから環境変数を読み込む
load_dotenv()

# .env内にあるAPIキーを使う
openai.api_key = os.getenv("OPENAI_API_KEY")

# クールダウン管理の状態保持（グローバル変数かクラス内の属性が理想）
cooldown_status = {}










##　実際のアクションリスト














##オムニの応答とその後の反応















