from datetime import datetime, date, time, timedelta
from habit_awareness import *

T = datetime(2026, 10, 17, 12)
def mk(kind="vape"):
    d = Dashboard(); dev = BTDevice("d", kind); d.pair(dev); return d, dev

def test_never_blocks():
    d, v = mk(); d.set_threshold("d", 1)
    for _ in range(100): assert v.record(d, T, 1)["allowed"] is True
    assert d.day_total("d", T.date()) == 100
def test_never_blocks_when_off(): d, v = mk(); d.turn_off("d"); assert v.record(d, T)["allowed"]
def test_off_no_notifications():
    d, v = mk(); d.turn_off("d"); v.record(d, T); assert d.notifications == [] and d.events == []
def test_mute_logs_silently():
    d, v = mk(); d.mute("d"); v.record(d, T); assert d.notifications == [] and len(d.events) == 1
def test_unmute(): d, v = mk(); d.mute("d"); d.unmute("d"); v.record(d, T); assert len(d.notifications) == 1
def test_snooze():
    d, v = mk(); d.snooze("d", T + timedelta(hours=1)); v.record(d, T); assert d.notifications == []
    v.record(d, T + timedelta(hours=2)); assert len(d.notifications) == 1
def test_quiet_hours_hold():
    d, v = mk(); v.record(d, datetime(2026, 10, 17, 23)); assert d.notifications == [] and len(d.held) == 1
    d.release_held(); assert len(d.notifications) == 1
def test_baseline():
    d, v = mk()
    for i, n in enumerate([10, 20, 30], 1): v.record(d, T - timedelta(days=i), n)
    assert d.baseline("d", T.date()) == 20
def test_baseline_none(): d, v = mk(); assert d.baseline("d", T.date()) is None
def test_usual_message():
    d, v = mk()
    for i in range(1, 8): v.record(d, T - timedelta(days=i), 14)
    v.record(d, T, 14); assert "14 puffs today" in d.notifications[-1]["text"] and "about your usual" in d.notifications[-1]["text"]
def test_vape_guess_label(): d, v = mk(); v.record(d, T, 5); assert "GUESS" in d.notifications[0]["text"]
def test_no_default_threshold():
    d, v = mk("caffeine"); assert d.settings["d"].threshold is None
    v.record(d, T, 900); assert "asked me" not in d.notifications[0]["text"]
def test_user_threshold():
    d, v = mk("caffeine"); d.set_threshold("d", 300); v.record(d, T, 320)
    assert "300" in d.notifications[0]["text"]
def test_no_shaming():
    for line in demo():
        assert not any(w in line.lower() for w in BANNED_WORDS), line
def test_taper_only_opt_in():
    d, v = mk()
    for i in range(1, 8): v.record(d, T - timedelta(days=i), 20)
    v.record(d, T, 1); assert "taper" not in d.notifications[-1]["text"]
    d.opt_in_taper("d", T.date()); assert d.taper_target("d", T.date()) is not None
    d.opt_out_taper("d"); assert d.taper_target("d", T.date()) is None
def test_taper_math():
    d, v = mk()
    for i in range(1, 8): v.record(d, T - timedelta(days=i), 20)
    d.opt_in_taper("d", T.date(), 10); assert d.taper_target("d", T.date() + timedelta(days=14)) == 16.2
def test_export_delete():
    d, v = mk(); v.record(d, T); assert '"amount": 1' in d.export()
    d.delete_all(); assert d.events == [] and d.notifications == []
def test_references_not_rules():
    assert all("reference" in v.lower() or "guess" in v.lower() for v in REFERENCES.values())
def test_demo(): assert len(demo()) == 3
