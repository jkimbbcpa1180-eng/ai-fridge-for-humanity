"""Conflict-of-interest firewall. CC0 1.0 - credited to humanity. Synthetic data only.
Integrates with data_credit_ledger (consent, k-anonymity, hash-chained Ledger)."""
from __future__ import annotations
import hashlib, json
from data_credit_ledger import CreditProgram, Ledger, K

class COIViolation(Exception): pass
class BannedUse(Exception): pass

BANNED_PURPOSES = {"marketing", "heavy_user_targeting", "consumption_rewards"}
NICOTINE_MIN_AGE = 21

def h(obj): return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()

class Firewall:
    def __init__(self, board: set, researchers: set, embargo_days=180):
        self.board, self.researchers = set(board), set(researchers)
        self.embargo_days = embargo_days
        self.funders: dict = {}; self.pool = 0.0
        self.studies: dict = {}; self.published: list = []
        self.audit = Ledger(); self.program = CreditProgram()
    def _log(self, actor, event, **kw): self.audit.append({"actor": actor, "event": event, **kw})

    # blind fund
    def deposit(self, funder, amount):
        self.funders[funder] = self.funders.get(funder, 0) + amount; self.pool += amount
        self._log(funder, "deposit", amount=amount)
    def propose(self, actor, study, purpose, topic, min_age=18, researcher=None):
        if actor in self.funders and researcher is not None:
            self._log(actor, "rejected_pick_researcher", study=study)
            raise COIViolation("funders cannot pick researchers")
        if purpose in BANNED_PURPOSES:
            self._log(actor, "rejected_banned_use", study=study, purpose=purpose)
            raise BannedUse(f"banned use: {purpose}")
        if topic == "nicotine" and min_age < NICOTINE_MIN_AGE:
            self._log(actor, "rejected_youth_nicotine", study=study)
            raise BannedUse("no nicotine data from under-21s")
        self.studies[study] = {"purpose": purpose, "topic": topic, "researcher": None, "prereg": None,
                               "results": [], "funders": sorted(self.funders)}
        self._log(actor, "proposed", study=study, purpose=purpose)
    def assign(self, board_member, study, researcher):
        if board_member not in self.board: raise COIViolation("only the independent board assigns")
        if researcher in self.funders: raise COIViolation("researcher cannot be a funder")
        if researcher not in self.researchers: raise COIViolation("unknown researcher")
        self.studies[study]["researcher"] = researcher; self._log(board_member, "assigned", study=study, researcher=researcher)

    # pre-registration
    def preregister(self, researcher, study, hypotheses, metrics, t):
        s = self.studies[study]
        if s["researcher"] != researcher: raise COIViolation("not the assigned researcher")
        if s["prereg"]: raise COIViolation("prereg is locked")
        s["prereg"] = {"hash": h({"hypotheses": hypotheses, "metrics": sorted(metrics)}),
                       "metrics": sorted(metrics), "t": t}
        self._log(researcher, "preregistered", study=study, prereg_hash=s["prereg"]["hash"], t=t)
    def get_raw(self, actor, study):
        s = self.studies[study]
        if actor in self.funders: raise COIViolation("funders never access raw data")
        if actor != s["researcher"]: raise COIViolation("not the assigned researcher")
        if not s["prereg"]: raise COIViolation("preregister before data access")
        self._log(actor, "raw_access", study=study)
        return {u: list(r) for u, r in self.program.data.get(study, {}).items()}

    # results
    def submit_result(self, researcher, study, metric, value, t, finding="null"):
        s = self.studies[study]
        if s["researcher"] != researcher: raise COIViolation("not the assigned researcher")
        r = {"study": study, "metric": metric, "value": value, "finding": finding, "t": t,
             "prereg_match": metric in s["prereg"]["metrics"],
             "flag": None if metric in s["prereg"]["metrics"] else "not pre-registered (exploratory)",
             "funding_disclosure": {"funders": sorted(self.funders), "via": "blind pooled fund"},
             "published": False}
        s["results"].append(r); self._log(researcher, "result_submitted", study=study, metric=metric, finding=finding)
        return r
    def view_results(self, actor, study):
        rs = self.studies[study]["results"]
        if actor in self.funders: return [r for r in rs if r["published"]]  # no early look
        return rs
    def tick(self, today: int):
        """Auto-publish ALL results (null/negative too) after embargo. Days as ints for simplicity."""
        out = []
        for s in self.studies.values():
            for r in s["results"]:
                if not r["published"] and today - r["t"] >= self.embargo_days:
                    r["published"] = True; self.published.append(r); out.append(r)
                    self._log("system", "published", study=r["study"], metric=r["metric"], finding=r["finding"])
        return out
    def open_aggregate(self, study, key): return self.program.aggregate(study, key)  # k>=5 enforced there

def demo():
    fw = Firewall(board={"board_a"}, researchers={"res_1"}); p = fw.program; out = []
    fw.deposit("BeverageCo", 50000)
    try: fw.propose("BeverageCo", "s1", "health_research", "caffeine", researcher="res_1")
    except COIViolation as e: out.append(f"funder picks researcher -> {e}")
    for bad, kw in [("marketing", {}), ("health_research", {"topic": "nicotine", "min_age": 18})]:
        try: fw.propose("BeverageCo", "x", bad, kw.get("topic", "caffeine"), kw.get("min_age", 18))
        except BannedUse as e: out.append(f"rejected -> {e}")
    fw.propose("BeverageCo", "s1", "health_research", "caffeine")
    fw.assign("board_a", "s1", "res_1")
    try: fw.get_raw("res_1", "s1")
    except COIViolation as e: out.append(f"raw before prereg -> {e}")
    fw.preregister("res_1", "s1", ["late caffeine shortens sleep"], ["sleep_h"], t=0)
    for i in range(6):
        u = f"u{i}"; p.opt_in(u, "s1"); p.submit_day(u, "s1", "d1", {"sleep_h": 6 + i * 0.2}, {"sleep_h": 6 + i * 0.2})
    try: fw.get_raw("BeverageCo", "s1")
    except COIViolation as e: out.append(f"funder raw -> {e}")
    fw.submit_result("res_1", "s1", "sleep_h", -0.4, t=10, finding="negative")
    r2 = fw.submit_result("res_1", "s1", "mood", 0.0, t=10, finding="null")
    out.append(f"unregistered metric flag -> {r2['flag']}")
    out.append(f"funder sees early: {len(fw.view_results('BeverageCo', 's1'))} results")
    out.append(f"auto-published at day 190: {[(r['metric'], r['finding']) for r in fw.tick(190)]}")
    out.append(f"disclosure: {fw.published[0]['funding_disclosure']}")
    out.append(f"open aggregate: {fw.open_aggregate('s1', 'sleep_h')}")
    out.append(f"audit entries {len(fw.audit.rows)}, chain valid {fw.audit.verify()}")
    return out

if __name__ == "__main__": print("\n".join(demo()))
