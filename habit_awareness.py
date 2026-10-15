"""Habit awareness: NOTIFICATIONS ONLY. CC0 1.0 - credited to humanity.
Never blocks, locks or limits anything. The user keeps full control.
Synthetic data only. Not medical advice."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta

NICOTINE_MG_PER_PUFF_GUESS = 0.1  # GUESS: varies widely by device/liquid (~0.05-0.2+)

# Reference points only. NOT rules, NOT defaults, never enforced.
REFERENCES = {
    "caffeine_mg": "FDA: up to ~400 mg/day is not generally associated with negative effects in healthy adults (reference, not a rule).",
    "alcohol_drinks": "CDC/Dietary Guidelines (2020-2025): if you drink, 2 or fewer drinks/day for men, 1 or fewer for women (reference, not a rule; guidance may have been updated).",
    "nicotine_mg": "No standard daily reference; per-puff nicotine here is a GUESS.",
}
UNITS = {"vape": "puffs", "caffeine": "mg caffeine", "alcohol": "standard drinks"}

@dataclass
class BTDevice:
    """Simulated Bluetooth device. record() always succeeds: nothing is ever blocked."""
    dev_id: str; kind: str  # vape | caffeine | alcohol
    def record(self, dash: "Dashboard", t: datetime, amount: float = 1.0):
        dash._ingest(self, t, amount)
        return {"allowed": True, "recorded": amount}

@dataclass
class DeviceSettings:
    mode: str = "on"            # on | muted | off
    snooze_until: datetime | None = None
    threshold: float | None = None  # user-set only; None by default

class Dashboard:
    def __init__(self, quiet=(time(22, 0), time(7, 0))):
        self.events: list[dict] = []; self.settings: dict[str, DeviceSettings] = {}
        self.kinds: dict[str, str] = {}; self.quiet = quiet
        self.notifications: list[dict] = []; self.held: list[dict] = []
        self.taper: dict[str, dict] = {}
    def pair(self, d: BTDevice): self.settings.setdefault(d.dev_id, DeviceSettings()); self.kinds[d.dev_id] = d.kind
    def mute(self, dev): self.settings[dev].mode = "muted"
    def unmute(self, dev): self.settings[dev].mode = "on"
    def turn_off(self, dev): self.settings[dev].mode = "off"
    def snooze(self, dev, until): self.settings[dev].snooze_until = until
    def set_threshold(self, dev, v): self.settings[dev].threshold = v
    def opt_in_taper(self, dev, start: date, weekly_pct=10):
        self.taper[dev] = {"start": start, "weekly_pct": weekly_pct}
    def opt_out_taper(self, dev): self.taper.pop(dev, None)

    def _ingest(self, d, t, amount):
        if d.dev_id not in self.settings: self.pair(d)
        if self.settings[d.dev_id].mode == "off": return  # off: nothing logged, nothing sent
        self.events.append({"dev": d.dev_id, "kind": d.kind, "t": t.isoformat(), "amount": amount})
        self._maybe_notify(d.dev_id, t)

    def day_total(self, dev, day: date):
        return sum(e["amount"] for e in self.events if e["dev"] == dev and e["t"][:10] == day.isoformat())
    def baseline(self, dev, day: date, days=7):
        """Mean of previous `days` days that have any data (days with 0 excluded)."""
        vals = [self.day_total(dev, day - timedelta(days=i)) for i in range(1, days + 1)]
        vals = [v for v in vals if v > 0]
        return sum(vals) / len(vals) if vals else None
    def taper_target(self, dev, day):
        p = self.taper.get(dev); b = self.baseline(dev, p["start"]) if p else None
        if not p or b is None: return None
        weeks = max(0, (day - p["start"]).days // 7)
        return round(b * (1 - p["weekly_pct"] / 100) ** weeks, 1)

    def _in_quiet(self, t):
        a, b = self.quiet
        return (t.time() >= a or t.time() < b) if a > b else (a <= t.time() < b)
    def message(self, dev, day):
        kind = self.kinds[dev]; n = self.day_total(dev, day); b = self.baseline(dev, day)
        if kind == "vape":
            amt = f"{n:g} puffs today (about {n*NICOTINE_MG_PER_PUFF_GUESS:.1f} mg nicotine, GUESS)"
        else: amt = f"{n:g} {UNITS[kind]} today"
        if b is None: rel = "no baseline yet"
        elif abs(n - b) <= 0.15 * b: rel = "about your usual"
        elif n > b: rel = f"a bit above your usual {b:.0f}"
        else: rel = f"a bit below your usual {b:.0f}"
        msg = f"Hey, {amt}, {rel}."
        s = self.settings[dev]
        if s.threshold is not None and n >= s.threshold: msg += f" You asked me to mention when you reach {s.threshold:g}."
        tt = self.taper_target(dev, day)
        if tt is not None: msg += f" Your opt-in taper goal today: {tt:g}. Totally your call."
        return msg
    def _maybe_notify(self, dev, t):
        s = self.settings[dev]
        if s.mode != "on": return
        if s.snooze_until and t < s.snooze_until: return
        n = {"dev": dev, "t": t.isoformat(), "text": self.message(dev, t.date())}
        (self.held if self._in_quiet(t) else self.notifications).append(n)
    def release_held(self):
        out, self.held = self.held, []; self.notifications += out; return out

    def export(self): return json.dumps({"events": self.events, "notifications": self.notifications})
    def delete_all(self): self.events.clear(); self.notifications.clear(); self.held.clear()

BANNED_WORDS = ("bad", "shame", "should", "must", "failed", "addict", "too much", "stop")

def demo():
    dash = Dashboard(); vape = BTDevice("vape-1", "vape"); cof = BTDevice("coffee-1", "caffeine")
    alc = BTDevice("alc-1", "alcohol")
    for d in (vape, cof, alc): dash.pair(d)
    today = date(2026, 10, 17)
    for i in range(1, 8):
        day = datetime.combine(today - timedelta(days=i), time(12))
        vape.record(dash, day, 14); cof.record(dash, day, 250); alc.record(dash, day, 1)
    dash.set_threshold("coffee-1", 300)
    dash.opt_in_taper("vape-1", today)
    vape.record(dash, datetime.combine(today, time(15)), 14)
    cof.record(dash, datetime.combine(today, time(9)), 320)
    alc.record(dash, datetime.combine(today, time(23)), 2)  # quiet hours: held
    dash.notifications = [n for n in dash.notifications if n["t"][:10] == today.isoformat()]
    return [n["text"] for n in dash.notifications] + ["(held for morning) " + n["text"] for n in dash.held]

if __name__ == "__main__":
    print("\n".join(demo()))
