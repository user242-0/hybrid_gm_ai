hybrid_gm_ai/
└── src/
    └── actions/(アクションの定義)
        ├── __init__.py（各関数をまとめてimport）
        ├── exploration.py（探索関連の関数）
        ├── combat.py（戦闘関連の関数）
        ├── npc_interactions.py（NPC関連の関数）
        └── utility.py（共通ユーティリティ関数）
    ├── action_definitions.py（アクションリスト。AI(GM_AI)が登録していく方針）
    ├── (action_functions.py(アクションの関数定義ファイル。AIの提案が採択された場合、人（GM_human）が記述する方針))
    ├── CharacterStatus.py.py(キャラクターのステータス定義ファイル)
    ├── simulation.py(シミュレーション本体)
    ├── requirements_checker.py(行動が可能かチェックする機能)
    ├── logger.py(プレイヤーの行動を記録)
    └── conversation_manager.py(会話の状況・状態の管理。会話の中身は扱わない)
└── scripts/
    ├──generate_rules_APItest.py（APIでログからルール作成するスクリプト）
    └──parse_ai_response_to_json（LLMの生成したルールをパースしてjsonに使いやすくまとめる）
└── data/
    └──logs
        ├── gameplay_log_latest.json
        ├── gameplay_log_previous.json
        └── archive/
            └── （古いログをここに退避）
    └──rules
        ├── ai_rules_raw_latest.txt
        ├── ai_generated_rules_latest.json
        └── archive/
            └── （古いルールをここに退避）