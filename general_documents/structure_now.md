hybrid_gm_ai/
└── src/
    └── actions/(アクションの定義)
        ├── __init__.py（各関数をまとめてimport）
        ├── exploration.py（探索関連の関数）
        ├── combat.py（戦闘関連の関数）
        ├── npc_interactions.py（NPC関連の関数）
        └── utility.py（共通ユーティリティ関数）
    ├── action_definitions.py（アクションリスト。AI(GM_AI)が登録していく方針）
    ├── CharacterStatus.py.py(キャラクターのステータス定義ファイル)
    ├── simulation.py(シミュレーション本体)
    ├── requirements_checker.py(行動が可能かチェックする機能)
    ├── logger.py(プレイヤーの行動を記録)
    └── conversation_manager.py(会話の状況・状態の管理。会話の中身は扱わない)
└── scripts/
    └──test/
        └── test_switch_rc.py（今回走らせたいプログラム）