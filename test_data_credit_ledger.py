import pytest
from data_credit_ledger import *
S = "s"
def prog(*users):
    p = CreditProgram()
    for u in users: p.opt_in(u, S)
    return p
def bal(p, u): return p.ledger.balance(pseudonym(u, S))

def test_sick_equals_healthy():
    p = prog("h", "sick")
    p.submit_day("h", S, "d1", {"sleep_h": 8, "steps": 12000}, {"sleep_h": 8, "steps": 12000})
    p.submit_day("sick", S, "d1", {"sleep_h": 3, "steps": 200}, {"sleep_h": 3, "steps": 200})
    assert bal(p, "h") == bal(p, "sick") == CREDITS_PER_HONEST_DAY
def test_faked_zero_flagged():
    p = prog("f"); r = p.submit_day("f", S, "d1", {"sleep_h": 3}, {"sleep_h": 9})
    assert r["credited"] == 0 and r["flag"] and bal(p, "f") == 0
def test_fake_no_penalty():
    p = prog("f"); p.submit_day("f", S, "d1", {"x": 1}, {"x": 1}); p.submit_day("f", S, "d2", {"x": 1}, {"x": 50})
    assert bal(p, "f") == 10
def test_tolerance(): assert honest({"x": 7.0}, {"x": 7.5}) and not honest({"x": 7}, {"x": 10})
def test_no_shared_fields_not_honest(): assert not honest({"a": 1}, {"b": 1})
def test_not_opted_in():
    p = CreditProgram(); assert p.submit_day("x", S, "d", {"a": 1}, {"a": 1})["credited"] == 0
def test_revoke_stops_earning():
    p = prog("u"); p.submit_day("u", S, "d1", {"a": 1}, {"a": 1}); p.revoke("u", S)
    assert p.submit_day("u", S, "d2", {"a": 1}, {"a": 1})["credited"] == 0 and bal(p, "u") == 10
    assert "u" not in p.data[S]
def test_tamper_detected():
    p = prog("u"); p.submit_day("u", S, "d1", {"a": 1}, {"a": 1}); assert p.ledger.verify()
    p.ledger._rows[1]["credits"] = 9999; assert not p.ledger.verify()
def test_tamper_delete_detected():
    p = prog("u", "v"); del p.ledger._rows[0]; assert not p.ledger.verify()
def test_rows_are_copies():
    p = prog("u"); p.ledger.rows[0]["credits"] = 5; assert p.ledger.verify()
def test_k_anonymity():
    p = prog(*"abcd")
    for u in "abcd": p.submit_day(u, S, "d", {"sleep_h": 6}, {"sleep_h": 6})
    assert p.aggregate(S, "sleep_h")["suppressed"]
    p.opt_in("e", S); p.submit_day("e", S, "d", {"sleep_h": 6}, {"sleep_h": 6})
    assert p.aggregate(S, "sleep_h") == {"n_users": 5, "mean": 6.0}
def test_no_raw_names_in_ledger():
    p = prog("alice"); assert "alice" not in json.dumps(p.ledger.rows)
def test_crypto_off():
    assert CRYPTO_EXPORT_ENABLED is False
    with pytest.raises(NotImplementedError): CreditProgram().export_crypto()
def test_demo():
    out = demo(); assert out[0] == "healthy: 30 credits" and out[1] == "sick: 30 credits" and "faker: 0 credits" in out
