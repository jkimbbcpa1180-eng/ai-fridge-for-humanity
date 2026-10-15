# Real Mode AI Fridge (demo)
CC0 1.0. Credited to humanity. Synthetic data only. Not medical advice. Values marked GUESS are judgment.

Run `python3 realmode_ai_fridge.py` (writes `demo_output.txt`). Run `python3 -m pytest -q` (32 tests).

## What it models
1. **Hardware AI switch per device:** OFF (invisible), WATCH (read/suggest), AI_POWER (act within limits; risky actions need owner confirm). Only `physical_flip` changes it, and software assignment raises an error. Every action is logged.
2. **Gateway (MCP-style):** `list_devices`, `get_state`, `do_action`; scoped, revocable tokens per device and action; results include the device state read back afterwards.
3. **Drink maker:** chipped cartridges (water, CO2, syrup, protein, vitamins, electrolytes, fiber, caffeine) with level, expiry and allergens.
4. **Firmware hard limits** (the AI cannot override them): vitamin D 100 mcg, vitamin A 3000 mcg RAE, iron 45 mg (NIH ODS adult ULs); caffeine 400 mg/day (FDA). Child profile: NIH UL for ages 4–8, and caffeine 0 (a design choice). Allergen lockouts and expiry checks.
5. **Health link:** per-field opt-in; finds gaps; out-of-range labs produce "see a doctor" and never a bigger dose.
6. **Caffeine:** 5 h half-life (GUESS; range 3–7 h), bedtime residual range, personal cutoff that learns from sleep quality (GUESS rule), shift-work plan.
7. **Anti-greed:** any-brand cartridges, local-only, no subscription, export/delete, open protocol.
8. **Data-for-credit:** opt-in per study, name/location stripped, k≥5 suppression, credits, revocation, results returned to participants.

## Limitations (honest)
- This is a simulation. There is no real hardware, no Matter or MCP wire protocol and no real health-app API.
- The software "hardware switch" is enforced by Python convention, which is only a stand-in for a physical switch.
- Lab flag thresholds, nutrient targets and the cutoff-learning rule are GUESSES. Vitamin A UL applies to preformed A only.
- Pseudonymous hashes and k=5 do not guarantee anonymity; re-identification is still possible with rich data.
- Token scopes are in-memory with no auth crypto or persistence.

## Habit awareness (`habit_awareness.py`)
A module that only sends notifications. It never blocks, locks or limits anything, and you stay in full control.
- **Simulated Bluetooth devices:** vape (puffs, with estimated nicotine at 0.1 mg per puff, a GUESS), caffeine (mg) and alcohol (standard drinks).
- **Dashboard:** one dashboard owned by the user. It compares today with your 7-day baseline in friendly messages, for example "Hey, 14 puffs today, about your usual."
- **Thresholds:** none by default; you set them yourself. Reference points (FDA's ~400 mg/day caffeine, and the CDC / 2020–2025 Dietary Guidelines' ≤2 drinks/day for men and ≤1 for women) are shown as information only, never as rules.
- **Controls:** mute (keeps logging silently), snooze, or off (logs nothing) per device. Quiet hours (22:00–07:00 by default) hold messages until morning.
- **Taper plan:** an optional gentle plan, only if you opt in (default −10% per week). You can opt out anytime.
- **Tone:** messages are checked against a list of shaming words.
- **Your data:** stored locally, and you can export or delete it.
- **Limitations:** per-puff nicotine is a GUESS, the devices are simulated, and the alcohol guidance may have been updated since 2020–2025.

## Data-credit ledger (`data_credit_ledger.py`)
- **Equal pay per honest day:** every honest data-day earns the same 10 credits. Pay is for contributing, not for being healthy, so sick or struggling users earn exactly what healthy users earn.
- **Honesty check:** device readings are cross-checked against self-logs, allowing a 20% difference (a GUESS). A day that doesn't match earns 0 and is flagged, with no penalty and no clawback of past credits.
- **Ledger:** plain credits, append-only and SHA-256 hash-chained, so any edit or deletion is detectable. It isn't secret or signed, so it shows tampering but doesn't prevent it.
- **Studies:** you opt in per study and can revoke, which stops earning and removes your data. Aggregates are only shown when k≥5 users, and users appear only under pseudonyms.
- **Crypto export:** off by default and only a future idea. Crypto is volatile and full of scams.

## Conflict-of-interest firewall (`coi_firewall.py`)
Uses the consent, k≥5 and hash-chained ledger pieces from `data_credit_ledger`.
- **Blind fund:** funders deposit money into a shared pool. Only the independent board assigns researchers. The code enforces that funders can't pick a researcher, act as one, see results early or access raw data; any attempt raises an error.
- **Pre-registration:** hypotheses and metrics are hashed, timestamped and locked before anyone can access the data. Results on metrics that weren't pre-registered are flagged as exploratory.
- **Publishing:** every result, including null and negative ones, is auto-published when its embargo expires (180 days by default). Each result carries a funding disclosure.
- **Open data:** anonymized aggregates are open for reanalysis, but only once at least 5 users contribute (k≥5). Users opt in per study and can withdraw, which removes their data.
- **Banned uses:** marketing, targeting heavy users, rewards tied to consuming more, and nicotine data from anyone under 21 are all rejected and logged.
- **Audit log:** a hash-chained log shows tampering.
- **Limitations:** the rules are enforced only inside this code, while real independence needs legal and governance backing. Days are counted as integers. A board member could still collude with a funder, and a funder could fund through someone else.
