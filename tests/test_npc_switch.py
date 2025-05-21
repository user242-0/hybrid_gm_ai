from src.init_state import init_game_state
from src.scheduler import Scheduler
import src.simulation_e as sim
from src.choice_model import Choice


def test_npc_switch(monkeypatch):
    gs = init_game_state()
    luna = gs["party"]["Luna"]
    hero = gs["party"]["Hero"]

    local_sched = Scheduler()
    monkeypatch.setattr(sim, "scheduler", local_sched)

    switch_choice = Choice("switch_character", "switch_character", "green", 255)
    monkeypatch.setattr(sim, "select_action", lambda *args, **kwargs: switch_choice)

    sim.rc_tick(luna, gs)

    assert gs["active_char"] is hero
    assert not hero.is_npc
    assert luna.is_npc
    assert any(job[2] == sim.rc_tick and job[3][0] is luna for job in local_sched._queue)