from director.registry import synthesize_from_text


def test_registry_selects_pack():
    premise, goals, pack_id = synthesize_from_text("最強の従者を無理矢理従える凡俗な風来坊")
    assert pack_id == "rogue_master"
    assert "modes" in goals and isinstance(goals["modes"], dict)
    assert "title" in premise
