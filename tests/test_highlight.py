from sb_highlight import highlight_kind_for_term, term_is_ship


def test_caracal_is_ship_not_module():
    ships = {"caracal", "retribution", "basilisk"}
    modules = {"caracal", "sensor booster", "warp disruptor"}  # polluted module set
    # Ships win
    assert highlight_kind_for_term("Caracal", ship_terms=ships, module_terms=modules) == "ship"
    assert highlight_kind_for_term("Retribution", ship_terms=ships, module_terms=modules) == "ship"
    assert term_is_ship("Caracal", ships)


def test_module_only():
    assert highlight_kind_for_term("Warp Disruptor", ship_terms=set(), module_terms={"warp disruptor"}) == "module"
