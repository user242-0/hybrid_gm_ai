# scheduler.py
import heapq, time, itertools
class Scheduler:
    def __init__(self): self._queue, self._ids = [], itertools.count()
    def register(self, fn, delay, *a, **kw):
        heapq.heappush(self._queue, (time.time()+delay, next(self._ids), fn, a, kw))
    def run_once(self):
        if not self._queue or self._queue[0][0] > time.time(): return
        _, _, fn, a, kw = heapq.heappop(self._queue); fn(*a, **kw)
