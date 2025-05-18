from queue import Queue
event_q   = Queue()   # UI → Simulation（プレイヤー入力）
log_q     = Queue()   # Simulation → UI   （行動ログ）
