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
