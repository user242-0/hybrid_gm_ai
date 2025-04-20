hybrid_gm_ai/
└── src/
    ├── actions.py（アクションリスト。AI(GM_AI)が登録していく）
    ├── action_functions.py(アクションの関数定義ファイル。AIの提案が採択された場合、人（GM_human）が記述)
    ├── CharacterStatus.py.py(キャラクターのステータス定義ファイル)
    ├── simulation.py(シミュレーション本体)
    └── requirements_checker.py(行動が可能かチェックする機能)
└── scripts/
    └──generate_rules_APItest.py（APIでログからルール作成するスクリプト。セッション2で作成）
└── data/
    └──logs
        ├── example_log_01.json(セッション1でchatgptが作成したダミーログ)
        └── gameplay_log.json（セッション2でサンプルとして録った実際のログ）
    └──rules
        └── example_rules_01.json(セッション1でchatgptがexample_log_01.jsonから作成したルール)
        └── ai_generated_rules.json（セッション2で実際のログgameplay_log.jsonから作成したルール）