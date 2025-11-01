hybrid_gm_ai/
├─ src/
│  ├─ gmcore/              # 既存のゲーム進行（ループ、状態、行動ログ）
│  ├─ schemas/             # ★Pydantic等でYAML契約（scene_graph, style_card, preference_pair）
│  ├─ datalab/             # ★“データ工房”機能（emitters, action_registry, evaluators）
│  ├─ training/            # LoRA/DPO/CPTの最小ハーネス（ローカル用）
│  ├─ adapters/            # 画像/3D生成系のブリッジ（SD, pose/depth/normal提供など）
│  └─ runners/             # 実行エントリ（prod＝ゲーム／lab＝データ工房）
├─ jobs/                   # 生成物（Git管理外）
│  ├─snapshots/            # A/B の保管庫（画像・SG・メタ）
│  │ A/<run-id>/<case>/...
│  │ B/<run-id>/<case>/...
│  └─prefs/                # 選好ログ（preference_*.yml / priority_suggestions.yaml）
├─ data/
│  ├─ style_images/        # LoRA学習画像（多視点レンダ等）
│  └─ eval_set/            # 固定の“合格例”一式
├─ scripts/                # CLI（emit, train_lora, triage_ui, etc.）
└─ tests/                  # 契約テスト（YAMLバリデーション等）
