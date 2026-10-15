import pytest
from datetime import date, datetime, timedelta
from realmode_ai_fridge import *

D = date(2026, 10, 17)
def setup(pos=SwitchPos.AI_POWER, scopes=None):
    f = build(D); gw = Gateway(); gw.add(f); f.switch.physical_flip(pos)
    t = gw.issue_token({"fridge-1": scopes or {"read", "make_drink", "set_temp"}}); return f, gw, t

def test_switch_no_software_set():
    f = build(D)
    with pytest.raises(AttributeError): f.switch.position = SwitchPos.AI_POWER
    with pytest.raises(AttributeError): f.switch.pos = 1
def test_off_hides():
    f, gw, t = setup(SwitchPos.OFF)
    assert gw.list_devices(t) == []
    with pytest.raises(AccessDenied): gw.get_state(t, "fridge-1")
def test_watch_reads_not_acts():
    f, gw, t = setup(SwitchPos.WATCH)
    assert "cartridges" in gw.get_state(t, "fridge-1")
    with pytest.raises(AccessDenied): gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"water": 1})
def test_ai_power_acts_verified():
    f, gw, t = setup()
    r = gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"water": 1})
    assert r["verified_state"]["cartridges"]["water"]["level"] == pytest.approx(0.99)
def test_risky_needs_confirm():
    f, gw, t = setup()
    with pytest.raises(NeedsConfirmation): gw.do_action(t, "fridge-1", "set_temp", c=3)
    assert gw.do_action(t, "fridge-1", "set_temp", owner_confirmed=True, c=3)["temp_c"] == 3
def test_temp_range():
    f, gw, t = setup()
    with pytest.raises(LimitExceeded): gw.do_action(t, "fridge-1", "set_temp", owner_confirmed=True, c=20)
def test_log():
    f, gw, t = setup()
    gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"water": 1})
    with pytest.raises(NeedsConfirmation): gw.do_action(t, "fridge-1", "set_temp", c=3)
    assert [e["ok"] for e in f.log] == [True, False]
def test_manifest():
    f, gw, t = setup(); m = gw.list_devices(t)[0]
    assert "make_drink" in m["actions"] and m["risky"] == ["set_temp"]
def test_scope_limits():
    f, gw, t = setup(scopes={"read"})
    with pytest.raises(AccessDenied): gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"water": 1})
def test_revoke():
    f, gw, t = setup(); gw.revoke(t)
    with pytest.raises(AccessDenied): gw.list_devices(t)
def test_vitamin_d_cap():
    f, gw, t = setup()
    for _ in range(4): gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"vitamins": 5})
    assert f.totals("worker")["vitamin_d_mcg"] == 100
    with pytest.raises(LimitExceeded): gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"vitamins": 1})
def test_caffeine_cap():
    f, gw, t = setup()
    gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"caffeine": 10})
    with pytest.raises(LimitExceeded): gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"caffeine": 1})
def test_ul_values():
    assert UL == {"vitamin_d_mcg": 100, "vitamin_a_mcg_rae": 3000, "iron_mg": 45, "caffeine_mg": 400}
def test_cap_resets_next_day():
    f, gw, t = setup(); gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"caffeine": 10})
    f.today = D + timedelta(days=1)
    gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"caffeine": 1})
def test_allergen():
    f, gw, t = setup()
    with pytest.raises(LimitExceeded, match="allergen"): gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"protein": 1})
def test_child_no_caffeine():
    f, gw, t = setup()
    with pytest.raises(LimitExceeded): gw.do_action(t, "fridge-1", "make_drink", person="kid", recipe={"caffeine": 1})
def test_expired():
    f, gw, t = setup(); f.carts["fiber"].expiry = D - timedelta(days=1)
    with pytest.raises(LimitExceeded, match="expired"): gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"fiber": 1})
def test_any_brand():
    f = build(D); f.insert(Cartridge("syrup_lemon", "TotallyUnknownCo", 1, D + timedelta(days=5)))
    assert f.state()["cartridges"]["syrup_lemon"]["brand"] == "TotallyUnknownCo"
def test_low_report():
    assert "electrolytes" in build(D).state()["low"]
def test_health_optin():
    h = HealthLink({"steps": 20000}); assert h.read("steps") is None and h.gaps()["suggestions"] == []
    h.optin["steps"] = True; assert h.gaps()["suggestions"][0]["add"] == "electrolytes"
def test_food_gaps():
    h = HealthLink({"food_log": [{"protein_g": 30, "fiber_g": 30}]}); h.optin["food_log"] = True
    assert [s["add"] for s in h.gaps()["suggestions"]] == ["protein_g"]
def test_medical_flag_no_dose():
    h = HealthLink({"labs": {"ferritin_ng_ml": 5}}); h.optin["labs"] = True; g = h.gaps()
    assert "see a doctor" in g["flags"][0]["message"] and not any(s["add"] == "iron" for s in g["suggestions"])
def test_halflife():
    c = CaffeineModel(); t = datetime(2026, 1, 1, 12); c.add(t, 100)
    assert c.level(t + timedelta(hours=5)) == pytest.approx(50)
def test_residual_range():
    c = CaffeineModel(); t = datetime(2026, 1, 1, 12); c.add(t, 100)
    lo, hi = c.residual_range(t + timedelta(hours=10)); assert lo < c.level(t + timedelta(hours=10)) < hi
def test_cutoff_learning():
    c = CaffeineModel(); assert c.learn(0.4, 50) == 8; assert c.learn(0.9, 0) == 7.5
    for _ in range(10): c.learn(0.1, 100)
    assert c.cutoff_h_before_bed == 10
def test_shift_plan():
    p = shift_plan(datetime(2026, 10, 17, 3))
    assert p["bedtime"].hour == 13 and p["cutoff"].hour == 6 and p["boost"].hour == 2
def test_export_delete():
    f, gw, t = setup(); gw.do_action(t, "fridge-1", "make_drink", person="worker", recipe={"caffeine": 1})
    assert "worker" in export_data(f, "worker"); delete_data(f, "worker"); assert export_data(f, "worker") == "{}"
def test_anti_greed():
    assert ANTI_GREED["subscription_required"] is False and ANTI_GREED["all_features_local"]
def test_study_consent():
    h = StudyHub()
    with pytest.raises(AccessDenied): h.contribute("a", "s", {"x": 1})
def test_k_anon_strip_credit():
    h = StudyHub()
    for i in range(4): h.opt_in(i, "s"); h.contribute(i, "s", {"name": "n", "location": "l", "x": i})
    assert h.aggregate("s", "x")["suppressed"]
    h.opt_in(9, "s"); h.contribute(9, "s", {"x": 9}); assert h.aggregate("s", "x")["n"] == 5
    assert all("name" not in r and "location" not in r for _, r in h.records["s"].values()); assert h.credits[0] == 10
def test_revoke_and_results():
    h = StudyHub(); h.opt_in("a", "s"); h.contribute("a", "s", {"x": 1}); h.revoke("a", "s")
    assert "a" not in h.records["s"]; h.opt_in("b", "s"); h.publish_result("s", "finding")
    assert h.results == {"b": ["finding"]}
def test_demo_runs():
    assert len(demo()) > 10
