import pytest
from coi_firewall import *

def fw_ready():
    fw = Firewall({"b"}, {"r"}); fw.deposit("F", 100)
    fw.propose("F", "s", "health_research", "caffeine"); fw.assign("b", "s", "r"); return fw

def test_funder_cannot_pick():
    fw = Firewall({"b"}, {"r"}); fw.deposit("F", 1)
    with pytest.raises(COIViolation): fw.propose("F", "s", "health_research", "caffeine", researcher="r")
def test_only_board_assigns():
    fw = Firewall({"b"}, {"r"}); fw.deposit("F", 1); fw.propose("F", "s", "health_research", "caffeine")
    with pytest.raises(COIViolation): fw.assign("F", "s", "r")
def test_funder_not_researcher():
    fw = Firewall({"b"}, {"F"}); fw.deposit("F", 1); fw.propose("F", "s", "health_research", "c")
    with pytest.raises(COIViolation): fw.assign("b", "s", "F")
@pytest.mark.parametrize("p", sorted(BANNED_PURPOSES))
def test_banned(p):
    with pytest.raises(BannedUse): Firewall({"b"}, {"r"}).propose("x", "s", p, "caffeine")
def test_youth_nicotine():
    fw = Firewall({"b"}, {"r"})
    with pytest.raises(BannedUse): fw.propose("x", "s", "health_research", "nicotine", min_age=20)
    fw.propose("x", "s", "health_research", "nicotine", min_age=21)
def test_raw_needs_prereg():
    fw = fw_ready()
    with pytest.raises(COIViolation): fw.get_raw("r", "s")
    fw.preregister("r", "s", ["h"], ["m"], 0); assert fw.get_raw("r", "s") == {}
def test_funder_no_raw():
    fw = fw_ready(); fw.preregister("r", "s", ["h"], ["m"], 0)
    with pytest.raises(COIViolation): fw.get_raw("F", "s")
def test_prereg_locked_and_hashed():
    fw = fw_ready(); fw.preregister("r", "s", ["h"], ["m"], 0)
    assert len(fw.studies["s"]["prereg"]["hash"]) == 64
    with pytest.raises(COIViolation): fw.preregister("r", "s", ["h2"], ["m"], 1)
def test_unregistered_flagged():
    fw = fw_ready(); fw.preregister("r", "s", ["h"], ["m"], 0)
    assert fw.submit_result("r", "s", "m", 1, 0)["flag"] is None
    assert fw.submit_result("r", "s", "other", 1, 0)["flag"]
def test_no_early_view_and_autopublish_null():
    fw = fw_ready(); fw.preregister("r", "s", ["h"], ["m"], 0); fw.submit_result("r", "s", "m", 0, 0, "null")
    assert fw.view_results("F", "s") == [] and fw.tick(100) == []
    pub = fw.tick(180); assert pub[0]["finding"] == "null" and len(fw.view_results("F", "s")) == 1
def test_disclosure_attached():
    fw = fw_ready(); fw.preregister("r", "s", ["h"], ["m"], 0)
    assert fw.submit_result("r", "s", "m", 0, 0)["funding_disclosure"]["funders"] == ["F"]
def test_open_aggregate_k():
    fw = fw_ready(); p = fw.program
    for i in range(4): p.opt_in(i, "s"); p.submit_day(i, "s", "d", {"x": 1}, {"x": 1})
    assert fw.open_aggregate("s", "x")["suppressed"]
    p.opt_in(9, "s"); p.submit_day(9, "s", "d", {"x": 1}, {"x": 1}); assert fw.open_aggregate("s", "x")["n_users"] == 5
def test_withdrawal_removes_data():
    fw = fw_ready(); p = fw.program; p.opt_in("u", "s"); p.submit_day("u", "s", "d", {"x": 1}, {"x": 1})
    p.revoke("u", "s"); fw.preregister("r", "s", ["h"], ["x"], 0); assert "u" not in fw.get_raw("r", "s")
def test_audit_chain():
    fw = fw_ready(); assert fw.audit.verify(); fw.audit._rows[0]["amount"] = 0; assert not fw.audit.verify()
def test_rejections_audited():
    fw = Firewall({"b"}, {"r"})
    with pytest.raises(BannedUse): fw.propose("x", "s", "marketing", "c")
    assert fw.audit.rows[-1]["event"] == "rejected_banned_use"
def test_demo(): assert any("chain valid True" in l for l in demo())
