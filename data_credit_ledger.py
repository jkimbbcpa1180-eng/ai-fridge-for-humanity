"""Data-credit ledger. CC0 1.0 - credited to humanity. Synthetic data only.
Rewards honest data CONTRIBUTION, never health status: every honest data-day
earns the same, whether the user is healthy, sick or struggling.
Mismatched days earn 0 and are flagged - no penalty, no clawback."""
from __future__ import annotations
import hashlib, json

CREDITS_PER_HONEST_DAY = 10
TOLERANCE = 0.2  # GUESS: 20% relative mismatch allowed between device and self-log
CRYPTO_EXPORT_ENABLED = False  # Future idea only. Crypto is volatile and scam-prone; off by default.
K = 5

def honest(device: dict, self_log: dict, tol=TOLERANCE):
    """True if every field present in both agrees within tolerance."""
    shared = set(device) & set(self_log)
    if not shared: return False
    for k in shared:
        d, s = float(device[k]), float(self_log[k])
        if abs(d - s) > tol * max(abs(d), abs(s), 1): return False
    return True

class Ledger:
    """Append-only, hash-chained."""
    def __init__(self): self._rows: list[dict] = []
    def append(self, entry: dict):
        prev = self._rows[-1]["hash"] if self._rows else "0" * 64
        body = {"i": len(self._rows), "prev": prev, **entry}
        body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        self._rows.append(body); return body
    @property
    def rows(self): return [dict(r) for r in self._rows]  # copies; no in-place edit API
    def verify(self):
        prev = "0" * 64
        for i, r in enumerate(self._rows):
            b = {k: v for k, v in r.items() if k != "hash"}
            if r["prev"] != prev or r["i"] != i: return False
            if hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest() != r["hash"]: return False
            prev = r["hash"]
        return True
    def balance(self, pid): return sum(r.get("credits", 0) for r in self._rows if r.get("pid") == pid)

def pseudonym(user, study): return hashlib.sha256(f"{study}:{user}".encode()).hexdigest()[:12]

class CreditProgram:
    def __init__(self): self.ledger = Ledger(); self.consent: dict = {}; self.data: dict = {}
    def opt_in(self, user, study):
        self.consent.setdefault(study, set()).add(user)
        self.ledger.append({"event": "opt_in", "pid": pseudonym(user, study), "study": study, "credits": 0})
    def revoke(self, user, study):
        self.consent.get(study, set()).discard(user)
        self.data.get(study, {}).pop(user, None)
        self.ledger.append({"event": "revoke", "pid": pseudonym(user, study), "study": study, "credits": 0})
    def submit_day(self, user, study, day, device: dict, self_log: dict):
        pid = pseudonym(user, study)
        if user not in self.consent.get(study, set()):
            return {"credited": 0, "reason": "not opted in"}
        ok = honest(device, self_log)
        e = self.ledger.append({"event": "data_day", "pid": pid, "study": study, "day": day,
                                "credits": CREDITS_PER_HONEST_DAY if ok else 0,
                                "flag": None if ok else "device/self-log mismatch"})
        if ok: self.data.setdefault(study, {}).setdefault(user, []).append(device)
        return {"credited": e["credits"], "flag": e["flag"]}
    def aggregate(self, study, key):
        per_user = [sum(r[key] for r in rows) / len(rows)
                    for rows in self.data.get(study, {}).values() if rows and key in rows[0]]
        if len(per_user) < K: return {"suppressed": True, "reason": f"fewer than {K} users"}
        return {"n_users": len(per_user), "mean": round(sum(per_user) / len(per_user), 2)}
    def export_crypto(self, *_):
        if not CRYPTO_EXPORT_ENABLED:
            raise NotImplementedError("Crypto export is off: future idea only (volatility/scam risk).")

def demo():
    p = CreditProgram(); s = "sleep-study"
    users = {"healthy": 7.5, "sick": 4.0, "u3": 6, "u4": 6.5, "u5": 7, "faker": 8}
    for u in users: p.opt_in(u, s)
    for u, sleep in users.items():
        for d in range(1, 4):
            logged = 10 if u == "faker" else sleep
            p.submit_day(u, s, f"2026-10-{d:02d}", {"sleep_h": sleep if u != "faker" else 3}, {"sleep_h": logged})
    lines = [f"{u}: {p.ledger.balance(pseudonym(u, s))} credits" for u in users]
    lines.append(f"aggregate sleep_h: {p.aggregate(s, 'sleep_h')}")
    lines.append(f"chain valid: {p.ledger.verify()}")
    lines += [json.dumps({k: r[k] for k in ('i', 'event', 'pid', 'day', 'credits', 'flag') if k in r}) + f" hash={r['hash'][:10]}"
              for r in p.ledger.rows[6:9] + p.ledger.rows[-3:]]
    return lines

if __name__ == "__main__": print("\n".join(demo()))
