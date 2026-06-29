# Branch cleanup candidates - 2026-06-29

This note is an inventory only. Do not delete branches from this file alone.
All delete candidates require human confirmation before any destructive command.

## DO NOT DELETE

- `main`
  - Demo #1公開時点。`demo-001`タグあり。
- `staging/session50-actor-view`
  - 理由: 現在作業中。Session50以降の一時統合ブランチ。
  - merge済みか: 現在ブランチ
  - リモートにあるか: yes, `origin/staging/session50-actor-view`
  - 最終commit: `6059f6d` feat(This time): add actor-specific location and discovery view
- `demo-001` tag
  - Demo #1の復帰地点。タグは削除しない。

## KEEP

- `backup/pre-session26-20260207`
  - 理由: 明示的なバックアップブランチ。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/backup/pre-session26-20260207`
  - 最終commit: `cfd27ea` commiting config, diary
- `demo/youtube-demo-01`
  - 理由: YouTube Demo #1公開直前作業の参照点。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/demo/youtube-demo-01`
  - 最終commit: `982a99a` chore: add public default config
- `feature/session50-actor-location-discovery`
  - 理由: `main` と同じ `demo-001` 地点を指しているが、Session50前後の作業名として参照される可能性がある。
  - merge済みか: yes
  - リモートにあるか: no
  - 最終commit: `7a8c9d2` Merge pull request #2 from user242-0/demo/youtube-demo-01

## DELETE CANDIDATE / HUMAN CONFIRMATION REQUIRED

- `feature/actor-mode-by-actor-id`
  - 理由: Session48系の完了済み個別実装ブランチ。現在ブランチへ取り込み済み。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/feature/actor-mode-by-actor-id`
  - 最終commit: `429b891` fix(hud): expose actor mode for Director HUD verification
  - 注意点: 人間確認必須。Demo #1直後の参照が不要になってから削除する。
- `feature/actor-specific-microgoal`
  - 理由: Session49系の完了済み個別実装ブランチ。現在ブランチへ取り込み済み。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/feature/actor-specific-microgoal`
  - 最終commit: `44fab19` feat(director): add actor-specific micro goals
  - 注意点: 人間確認必須。
- `feature/demo-hud-cleanup`
  - 理由: Demo HUD cleanupの完了済み個別実装ブランチ。現在ブランチへ取り込み済み。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/feature/demo-hud-cleanup`
  - 最終commit: `05757ee` fix(hud): enable actor mode control in demo HUD
  - 注意点: 人間確認必須。
- `feature/demo-microgoal-polish`
  - 理由: 60秒デモ前ポリッシュの完了済み個別実装ブランチ。現在ブランチへ取り込み済み。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/feature/demo-microgoal-polish`
  - 最終commit: `5f6302c` fix(hud): hide unavailable actor micro goals
  - 注意点: 人間確認必須。
- `feature/huddemo-legibility-pass`
  - 理由: HUD_DEMO legibility passの完了済み個別実装ブランチ。現在ブランチへ取り込み済み。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/feature/huddemo-legibility-pass`
  - 最終commit: `48b02de` style(hud): improve demo HUD legibility
  - 注意点: 人間確認必須。
- `feature/rc-specific-hud-actions`
  - 理由: Session47-B系の完了済み個別実装ブランチ。現在ブランチへ取り込み済み。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/feature/rc-specific-hud-actions`
  - 最終commit: `15fd4ae` fix(hud): register trickster FLEE actions for execution
  - 注意点: 人間確認必須。
- `fix/test-all-green-before-main`
  - 理由: main更新前のテスト整備ブランチ。現在ブランチへ取り込み済み。
  - merge済みか: yes
  - リモートにあるか: no
  - 最終commit: `fd32706` docs: update README for current runtime
  - 注意点: 人間確認必須。

## REVIEW NEEDED

- `chore/repo-inventory-cleanup`
  - 理由: LOGBOOK/archive整理の履歴として残すか、削除候補にするか確認が必要。
  - merge済みか: yes
  - リモートにあるか: no
  - 最終commit: `4539799` chore: archive legacy files and trim LOGBOOK
- `codex/read-only-survey`
  - 理由: Codex試行用のcheckpointに見えるが、保持価値の確認が必要。
  - merge済みか: yes
  - リモートにあるか: no
  - 最終commit: `c56e5c9` checkpoint before codex trial
- `cursor-trial/microgoal-logging`
  - 理由: 旧基準ブランチとしてSTATEに残っていたため、今後も参照するか確認が必要。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/cursor-trial/microgoal-logging`
  - 最終commit: `32ed574` Feat: Affordance Bridge v2 — discovery/opportunity separation + governed actions (Session 32)
- `feature/action-proposal-actor-id-advisory`
  - 理由: Session45の中核ログに対応するブランチ。参照頻度が高い間は保持候補。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/feature/action-proposal-actor-id-advisory`
  - 最終commit: `66cd7da` docs:Session 45/ AI proposal with actor_id/Demo seeds
- `feature/action-proposal-dsl-v0.1-validator`
  - 理由: localがremoteよりahead 1。削除判断前に差分確認が必要。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/feature/action-proposal-dsl-v0.1-validator`
  - 最終commit: local `c4cacba` docs: record actor-specific HUD proposal direction / remote `ce4832d` docs: document action proposal advisory HUD display
- `feature/session30-affordance-bridge`
  - 理由: Session30-31系の履歴ブランチ。diaryとの対応を確認してから判断する。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/feature/session30-affordance-bridge`
  - 最終commit: `c2fa0da` Feat: HUD location display + debug dropdown (Session 31)
- `feature/session32-discovery-opportunity-separation`
  - 理由: Session32系の履歴ブランチ。`cursor-trial/microgoal-logging` と同一commit。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/feature/session32-discovery-opportunity-separation`
  - 最終commit: `32ed574` Feat: Affordance Bridge v2 — discovery/opportunity separation + governed actions (Session 32)
- `feature/session33-pack-unify-recommended-guard`
  - 理由: localがremoteよりahead 1。旧STATEで作業ブランチ扱いだったため、削除判断前に差分確認が必要。
  - merge済みか: yes
  - リモートにあるか: yes, `origin/feature/session33-pack-unify-recommended-guard`
  - 最終commit: local `c56e5c9` checkpoint before codex trial / remote `0bffe8e` Feat: Pack single source, Recommended governance, Action Proposal DSL v0.1 (Session 33)
- `origin/codex/action-proposal-validator-tests`
  - 理由: リモート専用ブランチ。localに対応ブランチがなく、用途確認が必要。
  - merge済みか: not checked locally
  - リモートにあるか: yes
  - 最終commit: `cb34790` docs: mark action proposal checks A-F implemented
- `origin/feature/session27-engagement-fight`
  - 理由: リモート専用ブランチ。Session27-29系の履歴として保持するか確認が必要。
  - merge済みか: not checked locally
  - リモートにあるか: yes
  - 最終commit: `6b28e95` Fix: enable combat actions & RO HUD display (Session 28+29)
