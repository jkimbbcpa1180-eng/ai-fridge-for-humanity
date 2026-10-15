"""Real Mode AI Fridge demo. CC0 1.0 - credited to humanity.
Synthetic data only. Values marked GUESS are judgment, not measured.
Upper limits: NIH ODS Tolerable Upper Intake Levels (adults 19+):
  vitamin D 100 mcg/day, vitamin A 3000 mcg RAE/day (preformed), iron 45 mg/day.
Caffeine 400 mg/day: FDA general guidance for healthy adults.
Not medical advice."""
from __future__ import annotations
import hashlib, json, math, secrets
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum

class SwitchPos(Enum):
    OFF = "off"; WATCH = "watch"; AI_POWER = "ai_power"

class AccessDenied(Exception): pass
class LimitExceeded(Exception): pass
class NeedsConfirmation(Exception): pass

class HardwareSwitch:
    """Physical switch. Only physical_flip (a person's hand) changes it."""
    def __init__(self, pos=SwitchPos.OFF): self.__pos = pos
    @property
    def position(self): return self.__pos
    def physical_flip(self, pos: SwitchPos): self.__pos = pos
    def __setattr__(self, k, v):
        if k != "_HardwareSwitch__pos": raise AttributeError("hardware switch")
        object.__setattr__(self, k, v)

UL = {"vitamin_d_mcg": 100.0, "vitamin_a_mcg_rae": 3000.0, "iron_mg": 45.0, "caffeine_mg": 400.0}
CHILD_UL = {"vitamin_d_mcg": 75.0, "vitamin_a_mcg_rae": 900.0, "iron_mg": 40.0, "caffeine_mg": 0.0}
# child: NIH UL ages 4-8 (D 75 mcg, A 900 mcg, iron 40 mg); caffeine 0 is a design choice.

@dataclass
class Cartridge:
    kind: str; brand: str; level: float; expiry: date
    per_unit: dict = field(default_factory=dict)   # nutrient per unit
    allergens: set = field(default_factory=set)
    chip_id: str = field(default_factory=lambda: secrets.token_hex(4))
    def report(self): return {"kind": self.kind, "brand": self.brand, "level": self.level,
                              "expiry": self.expiry.isoformat(), "chip": self.chip_id}

@dataclass
class Profile:
    name: str; child: bool = False; allergens: set = field(default_factory=set)
    def limits(self): return CHILD_UL if self.child else UL

class Device:
    def __init__(self, dev_id, kind, capabilities, risky=()):
        self.id, self.kind = dev_id, kind
        self.switch = HardwareSwitch()
        self.capabilities = capabilities; self.risky = set(risky)
        self.log: list = []
    def manifest(self): return {"id": self.id, "kind": self.kind, "actions": self.capabilities,
                                "risky": sorted(self.risky)}
    def state(self): return {"switch": self.switch.position.value}
    def _log(self, who, action, ok, detail):
        self.log.append({"t": len(self.log), "who": who, "action": action, "ok": ok, "detail": detail})

class Fridge(Device):
    def __init__(self, today: date):
        super().__init__("fridge-1", "fridge", {"make_drink": {"recipe": "dict unit amounts"},
                         "set_temp": {"min": 1, "max": 7, "unit": "C"}}, risky={"set_temp"})
        self.today = today; self.temp = 4.0
        self.carts: dict[str, Cartridge] = {}
        self.intake: dict[tuple, dict] = {}   # (person, date) -> totals
        self.profiles: dict[str, Profile] = {}
    def insert(self, c: Cartridge):  # anti-greed: any brand accepted, no DRM check
        self.carts[c.kind] = c
    def state(self):
        return {**super().state(), "temp_c": self.temp,
                "cartridges": {k: c.report() for k, c in self.carts.items()},
                "low": [k for k, c in self.carts.items() if c.level < 0.2]}
    def totals(self, person, d=None):
        return self.intake.setdefault((person, d or self.today), {k: 0.0 for k in UL})
    def check(self, person, recipe):
        """Device-enforced firmware check. Returns nutrient dict or raises."""
        p = self.profiles[person]; add = {k: 0.0 for k in UL}
        for kind, units in recipe.items():
            c = self.carts.get(kind)
            if not c: raise LimitExceeded(f"no cartridge {kind}")
            if c.expiry < self.today: raise LimitExceeded(f"{kind} expired")
            if c.level < units * 0.01: raise LimitExceeded(f"{kind} empty")
            if c.allergens & p.allergens: raise LimitExceeded(f"allergen lockout {c.allergens & p.allergens}")
            for n, v in c.per_unit.items():
                if n in add: add[n] += v * units
        t = self.totals(person)
        for n, v in add.items():
            if t[n] + v > p.limits()[n] + 1e-9:
                raise LimitExceeded(f"{n} would reach {t[n]+v:g} > cap {p.limits()[n]:g}")
        return add
    def make_drink(self, person, recipe):
        add = self.check(person, recipe)
        for kind, units in recipe.items(): self.carts[kind].level -= units * 0.01
        t = self.totals(person)
        for n, v in add.items(): t[n] += v
        return {"made": recipe, "for": person, "added": add, "totals_today": dict(t)}
    def set_temp(self, c):
        if not 1 <= c <= 7: raise LimitExceeded("temp out of range")
        self.temp = float(c); return {"temp_c": self.temp}

# ---------- gateway with scoped tokens (MCP-style tools) ----------
class Gateway:
    def __init__(self): self.devices: dict[str, Device] = {}; self.tokens: dict[str, dict] = {}
    def add(self, d): self.devices[d.id] = d
    def issue_token(self, scopes: dict):  # {device_id: {"read", "make_drink", ...}}
        t = secrets.token_urlsafe(12); self.tokens[t] = {k: set(v) for k, v in scopes.items()}; return t
    def revoke(self, t): self.tokens.pop(t, None)
    def _scope(self, t, dev, act):
        s = self.tokens.get(t)
        if s is None: raise AccessDenied("invalid or revoked token")
        if act not in s.get(dev, set()): raise AccessDenied(f"token lacks {act} on {dev}")
    def list_devices(self, t):
        s = self.tokens.get(t)
        if s is None: raise AccessDenied("invalid or revoked token")
        return [d.manifest() for k, d in self.devices.items()
                if k in s and d.switch.position != SwitchPos.OFF]
    def get_state(self, t, dev):
        self._scope(t, dev, "read"); d = self.devices[dev]
        if d.switch.position == SwitchPos.OFF: raise AccessDenied("switch OFF")
        return d.state()
    def do_action(self, t, dev, action, owner_confirmed=False, **kw):
        d = self.devices[dev]
        try:
            self._scope(t, dev, action)
            if d.switch.position != SwitchPos.AI_POWER:
                raise AccessDenied(f"switch {d.switch.position.value}: AI cannot act")
            if action in d.risky and not owner_confirmed:
                raise NeedsConfirmation(f"{action} needs owner confirmation")
            res = getattr(d, action)(**kw)
            res["verified_state"] = d.state()  # verified result read back from device
            d._log("ai", action, True, kw); return res
        except Exception as e:
            d._log("ai", action, False, str(e)); raise

# ---------- health link ----------
FIELDS = ("sleep", "steps", "food_log", "labs")
TARGETS = {"protein_g": 60, "fiber_g": 28}  # GUESS-level general adult targets
LAB_FLAGS = {"ferritin_ng_ml": (15, None), "vitamin_d_ng_ml": (12, None)}  # below = see doctor (GUESS thresholds)

class HealthLink:
    def __init__(self, data: dict): self.data = data; self.optin = {f: False for f in FIELDS}
    def read(self, f):
        if not self.optin.get(f): return None
        return self.data.get(f)
    def gaps(self):
        out = {"suggestions": [], "flags": [], "note": "Suggestions, not diagnosis."}
        food = self.read("food_log")
        if food:
            for n, tgt in TARGETS.items():
                have = sum(m.get(n, 0) for m in food)
                if have < tgt: out["suggestions"].append({"add": n, "gap": tgt - have})
        steps = self.read("steps")
        if steps and steps > 15000: out["suggestions"].append({"add": "electrolytes", "why": "high activity"})
        labs = self.read("labs") or {}
        for k, (lo, _) in LAB_FLAGS.items():
            if k in labs and labs[k] < lo:
                out["flags"].append({"lab": k, "value": labs[k],
                    "message": "Out of typical range: see a doctor. Dose NOT increased."})
        if labs.get("vitamin_d_ng_ml") is not None and 12 <= labs["vitamin_d_ng_ml"] < 20:
            out["suggestions"].append({"add": "vitamin_d", "why": "lab mildly low; stays under UL"})
        return out

# ---------- caffeine ----------
class CaffeineModel:
    def __init__(self, half_life_h=5.0):  # GUESS: 5 h typical, real range ~3-7 h
        self.half_life = half_life_h; self.doses: list[tuple[datetime, float]] = []
        self.cutoff_h_before_bed = 7.0
    def add(self, t, mg): self.doses.append((t, mg))
    def level(self, t):
        return sum(mg * 0.5 ** ((t - d).total_seconds() / 3600 / self.half_life)
                   for d, mg in self.doses if d <= t)
    def residual_range(self, t):  # GUESS range across 3-7 h half-lives
        lo, hi = CaffeineModel(3), CaffeineModel(7)
        lo.doses = hi.doses = self.doses
        return lo.level(t), hi.level(t)
    def cutoff(self, bedtime): return bedtime - timedelta(hours=self.cutoff_h_before_bed)
    def allowed(self, t, bedtime): return t < self.cutoff(bedtime)
    def learn(self, sleep_quality, residual_mg):
        """quality 0-1. Poor sleep with notable residual -> move cutoff 1h earlier (max 10h).
        Good sleep -> relax 0.5h (min 6h). Rule is a GUESS."""
        if sleep_quality < 0.6 and residual_mg > 30: self.cutoff_h_before_bed = min(10, self.cutoff_h_before_bed + 1)
        elif sleep_quality > 0.8: self.cutoff_h_before_bed = max(6, self.cutoff_h_before_bed - 0.5)
        return self.cutoff_h_before_bed

def shift_plan(shift_start: datetime, shift_h=8, sleep_after_h=2):
    """Shift-work mode: boost near start, cutoff well before post-shift sleep."""
    bed = shift_start + timedelta(hours=shift_h + sleep_after_h)
    return {"boost": shift_start - timedelta(minutes=30), "bedtime": bed,
            "cutoff": bed - timedelta(hours=7)}

# ---------- anti-greed ----------
ANTI_GREED = {
    "open_cartridges": "any brand or DIY refill accepted; chip reports only, never locks",
    "all_features_local": True, "subscription_required": False,
    "works_if_company_dies": "no cloud calls in this code path",
    "data_export_delete": True, "open_protocol": "JSON manifest + list_devices/get_state/do_action",
    "right_to_repair": "standard parts, published manuals (design commitment)",
}
def export_data(fridge, person):
    return json.dumps({f"{p}|{d}": v for (p, d), v in fridge.intake.items() if p == person})
def delete_data(fridge, person):
    for k in [k for k in fridge.intake if k[0] == person]: del fridge.intake[k]

# ---------- data-for-credit ----------
class StudyHub:
    K = 5
    def __init__(self): self.consent: dict = {}; self.records: dict = {}; self.credits: dict = {}; self.results: dict = {}
    def opt_in(self, user, study): self.consent.setdefault(study, set()).add(user)
    def revoke(self, user, study):
        self.consent.get(study, set()).discard(user); self.records.get(study, {}).pop(user, None)
    def contribute(self, user, study, record, credit=10):
        if user not in self.consent.get(study, set()): raise AccessDenied("no consent for this study")
        clean = {k: v for k, v in record.items() if k not in ("name", "location", "lat", "lon", "address")}
        pid = hashlib.sha256(f"{study}:{user}".encode()).hexdigest()[:10]
        self.records.setdefault(study, {})[user] = (pid, clean)
        self.credits[user] = self.credits.get(user, 0) + credit
    def aggregate(self, study, key):
        rows = [r for _, r in self.records.get(study, {}).values() if key in r]
        if len(rows) < self.K: return {"suppressed": True, "reason": f"n<{self.K} (k-anonymity)"}
        vals = [r[key] for r in rows]
        return {"n": len(vals), "mean": sum(vals) / len(vals)}
    def publish_result(self, study, text):
        for u in self.consent.get(study, set()): self.results.setdefault(u, []).append(text)

# ---------- demo ----------
def build(today):
    f = Fridge(today)
    exp = today + timedelta(days=60)
    for c in [Cartridge("water", "tap", 1.0, exp), Cartridge("co2", "GenericGas", 1.0, exp),
              Cartridge("syrup_lemon", "DIY", 0.5, exp),
              Cartridge("protein", "AnyBrand", 1.0, exp, {}, {"milk"}),
              Cartridge("protein_pea", "AnyBrand", 1.0, exp),
              Cartridge("vitamins", "OpenVit", 1.0, exp, {"vitamin_d_mcg": 5, "vitamin_a_mcg_rae": 150, "iron_mg": 2}),
              Cartridge("electrolytes", "OpenLyte", 0.15, exp),
              Cartridge("fiber", "OpenFiber", 1.0, exp),
              Cartridge("caffeine", "OpenCaf", 1.0, exp, {"caffeine_mg": 40})]:
        f.insert(c)
    f.profiles["worker"] = Profile("worker", allergens={"milk"})
    f.profiles["kid"] = Profile("kid", child=True)
    return f

def demo():
    out = []; p = out.append
    today = date(2026, 10, 17); f = build(today); gw = Gateway(); gw.add(f)
    tok = gw.issue_token({"fridge-1": {"read", "make_drink"}})
    try: gw.get_state(tok, "fridge-1")
    except AccessDenied as e: p(f"switch OFF -> {e}")
    f.switch.physical_flip(SwitchPos.WATCH)
    p(f"WATCH: low cartridges {gw.get_state(tok,'fridge-1')['low']}")
    try: gw.do_action(tok, "fridge-1", "make_drink", person="worker", recipe={"water": 1})
    except AccessDenied as e: p(f"WATCH act -> {e}")
    f.switch.physical_flip(SwitchPos.AI_POWER)
    plan = shift_plan(datetime(2026, 10, 17, 3, 0))
    p(f"shift plan: boost {plan['boost']:%H:%M}, cutoff {plan['cutoff']:%H:%M}, bed {plan['bedtime']:%H:%M}")
    cm = CaffeineModel()
    r = gw.do_action(tok, "fridge-1", "make_drink", person="worker",
                     recipe={"water": 3, "co2": 1, "caffeine": 4, "vitamins": 1}); cm.add(plan["boost"], 160)
    p(f"02:30 boost drink: caffeine {r['added']['caffeine_mg']:g} mg")
    try: gw.do_action(tok, "fridge-1", "make_drink", person="worker", recipe={"protein": 2})
    except LimitExceeded as e: p(f"whey -> {e}")
    hl = HealthLink({"sleep": {"hours": 5.5, "quality": 0.5}, "steps": 22000,
                     "food_log": [{"protein_g": 20, "fiber_g": 8}], "labs": {"ferritin_ng_ml": 10, "vitamin_d_ng_ml": 17}})
    for k in FIELDS: hl.optin[k] = True
    g = hl.gaps(); p(f"gaps: {[s['add'] for s in g['suggestions']]}; flags: {[x['message'] for x in g['flags']]}")
    r = gw.do_action(tok, "fridge-1", "make_drink", person="worker",
                     recipe={"water": 3, "protein_pea": 3, "fiber": 2, "electrolytes": 1})
    p(f"11:00 post-route drink made; electrolytes level now {r['verified_state']['cartridges']['electrolytes']['level']:.2f}")
    t = datetime(2026, 10, 17, 9, 0)
    p(f"09:00 more caffeine allowed? {cm.allowed(t, plan['bedtime'])}")
    lo, hi = cm.residual_range(plan["bedtime"])
    p(f"bedtime residual {cm.level(plan['bedtime']):.0f} mg (GUESS range {lo:.0f}-{hi:.0f})")
    p(f"cutoff learned: {cm.learn(0.5, cm.level(plan['bedtime']))} h before bed")
    try: gw.do_action(tok, "fridge-1", "make_drink", person="kid", recipe={"caffeine": 1})
    except LimitExceeded as e: p(f"kid caffeine -> {e}")
    try: gw.do_action(tok, "fridge-1", "make_drink", person="worker", recipe={"caffeine": 7})
    except LimitExceeded as e: p(f"over-cap -> {e}")
    try: gw.do_action(tok, "fridge-1", "set_temp", c=3)
    except AccessDenied as e: p(f"set_temp -> {e}")
    hub = StudyHub()
    for i in range(6):
        hub.opt_in(f"u{i}", "sleep-caffeine"); hub.contribute(f"u{i}", "sleep-caffeine",
            {"name": "x", "location": "y", "sleep_h": 5 + i * 0.5})
    p(f"study aggregate: {hub.aggregate('sleep-caffeine','sleep_h')}; u0 credits {hub.credits['u0']}")
    hub.revoke("u5", "sleep-caffeine"); hub.revoke("u4", "sleep-caffeine")
    p(f"after 2 revoke: {hub.aggregate('sleep-caffeine','sleep_h')}")
    gw.revoke(tok)
    try: gw.list_devices(tok)
    except AccessDenied as e: p(f"revoked token -> {e}")
    p(f"log entries: {len(f.log)}; anti-greed: subscription_required={ANTI_GREED['subscription_required']}")
    return out

if __name__ == "__main__":
    lines = demo(); print("\n".join(lines))
    open("demo_output.txt", "w").write("\n".join(lines) + "\n")
