🚩 おすすめのアップロード順序（具体例）
以下のような順番でファイルをアップロードすることをおすすめします。

プロジェクトの全体設計・定義

gm_ai_definition.md

structure.md

gm_ai_setting-direction.md

各スクリプトの役割・依存関係が記載されているファイル

actions.py

action_functions.py

CharacterStatus.py

requirements_checker.py

AI関連や外部APIとの連携

generate_rules_APItest.py

実行されるシミュレーション本体

simulation.py

実際のデータ（ログ、JSONルール）

example_log_01.json

gameplay_log.json

ai_generated_rules.json

example_rules_01.json