hybrid_gm_ai/
└── src
    ├── actions.py（アクションリスト。AI(GM_AI)が登録していく）
    ├── action_functions.py(アクションの関数定義ファイル。AIの提案が採択された場合、人（GM_human）が記述)
    ├── CharacterStatus.py.py(キャラクターのステータス定義ファイル)
    ├── simulation.py(シミュレーション本体)
    └── requirements_checker.py(行動が可能かチェックする機能)
└── data/
    └──logs
        ├── example_log_01.json(前回chatgptが作成したダミーログ)
        └── gameplay_log.json（サンプルとして今のログ）
    └──rules
        └── rules.json(前回chatgptがexample_log_01.jsonから作成したルール（アクションの提案）)