## 1. Core Concept
フルRCは、プレイヤーの同一シーン内ではローカル行動AIとして動く。
プレイヤーの視界外・別地点では、戦略的/物語的行動ログ生成モードで動く。
このログは後付けではなく、ゲーム時間の進行に合わせて実際に生成され、世界状態・痕跡・関係性に影響する。
switch_character時には、その蓄積ログと現在状態を参照し、その時点からローカル操作に切り替える。
## 2. RC Processing Modes
## 3. Same-scene Full RC Behavior
## 4. Off-screen Meaningful Action Log Generation
## 5. switch_character Transition
## 6. Full RC / Semi-RC / Simple NPC Distinction
## 7. Multiplayer Future Notes