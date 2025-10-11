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
    ├── requirements_checker.py(行動が可能かチェックする機能)
    ├── character_status.py(キャラクターのステータス定義ファイル)
    ├── choice_model.py(行動の定義ファイル)
    ├── choice_definitions.py(行動の色軸と、その値を定義。行動可能リストを挙げる機能も※choiceを定義しないと、実行可能でも行動可能から漏れる) 
    ├── choice_ui.py　(現在操作キャラクター actor に対して実行可能な Choice を列挙し、 GUI ログに出力する。)   
    ├── init_state.py(ゲームステータスの初期化)
    ├── simulation_e.py(シミュレーション本体)
    ├── simulation_utils.py(シミュレーションの効用関数。コマンドを Action に変換して実行機能)
    ├── control_manager.py(キャラ切り替えアクションの中身)
    ├── rc_ai.py （各キャラクターAI（Reversible Character）の制御）
    ├── emotion_state.py (感情値)
    ├── emotion_manager.py (感情値の設定アクションの中身)
    ├── emotion_math.py (感情値の計算関数群) 
    ├── emotion_perception.py (A(=observer) から見た B(=target) の心の空を生成）)
    ├── ui_emotion_mapper.py（キャラクターの emotion_color を UI 表示用の RGB に変換するユーティリティ）
    ├── gui.py (GUI関連の関数)
    ├── scheduler.py (スケジューラ)
    ├── event_bus.py (log_qとevent_qがQueue()で定義されてる)  
    ├── logger.py(プレイヤーの行動を記録)
    ├── conversation_manager.py(会話の状況・状態の管理。会話の中身は扱わない。最近はあまり使われてない)
    ├── quit_helper.py(「GUI Entry でも CLI input でも quit / exit / q を打てば安全終了」 を1 つの共通関数 で処理)    
    └── utility/
        ├── __init__.py
        ├── args_parser.py(アクション定義の中のargsにテンプレートがあれば、実際のものに置き換える)        
        └── targeting.py（ターゲティング関数群）       
└── scripts/
    ├──generate_rules_APItest.py（APIでログからルール作成するスクリプト）
    ├──parse_ai_response_to_json.py（LLMの生成したルールをパースしてjsonに使いやすくまとめる）
    ├──hearts_sky_pixel.py(ピクセル可視化デモ)
    └──loadenv_test.py(.envから環境変数を読み込む)
└── tests/
    ├──test_emotion_system.py（# セッション12 B〜E: emotion変換・知覚・要件ゲートの統合テスト）
    ├──test_npc_switch（npcがpcにswitchできるか）
    └──test_switch_rc.py(npcがpcにswitchできるか、簡易版)
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
