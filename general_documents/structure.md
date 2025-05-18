hybrid_gm_ai/
└── general_documents/(プロジェクト方針や日記、作業中に知ったことのメモも)
└── src/
    └── actions/(アクションの定義)
        ├── __init__.py（各関数をまとめてimport）
        ├── exploration.py（探索関連の関数）
        ├── combat.py（戦闘関連の関数）
        ├── npc_interactions.py（NPC関連の関数）
        └── utility.py（共通ユーティリティ関数）
    ├── action_definitions.py（アクションリスト。AI(GM_AI)が登録していく方針）
    ├── CharacterStatus.py(キャラクターのステータス定義ファイル)
    ├── init_state.py(ゲームステータスの初期化)
    ├── simulation.py(シミュレーション本体)
    ├── simulation_utils.py(シミュレーション内でコマンドを Action に変換して実行)
    ├── control_manager.py
    ├── requirements_checker.py(行動が可能かチェックする機能)
    ├── logger.py(プレイヤーの行動を記録)
    ├── conversation_manager.py(会話の状況・状態の管理。会話の中身は扱わない)
    ├── quit_helper.py(「GUI Entry でも CLI input でも quit / exit / q を打てば安全終了」 を1 つの共通関数 で処理)    
    └── utility/
        ├── __init__.py
        └── targeting.py（）       
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