# Decisions

Changes made after the spec in `CLAUDE.md` was frozen, with reasons.

---

## 2026-08-24 — β0 corrected from 0.048 to 0.035

**What happened:** `src/model.py` fits `Δlog(revenue)_t = β0 + β1·Δlog(spend)_t +
β2·Δlog(spend)_{t-1} + ε_t` on `data/dataset.csv`. `tests/test_model.py` recovers
β1=0.305 and β2=0.212, matching §3's table (0.301, 0.208) closely, and adjusted
R²=0.4725 matches §3's 0.471. β0 came out to 0.035, not the 0.048 written in §3.

**Root cause:** spec transcription error, not a data or code issue. §3's table mixed
sources: β1 and β2 were taken from the two-lag growth-with-carryover model, but β0 was
carried over from an earlier single-term model. Adding the carryover term absorbs part
of the trend that the single-term model's intercept was picking up, so the two-lag
model's true intercept is legitimately lower. Confirmed by refitting on the exact
committed dataset — the same fit that reproduces β1, β2, and R² to the values already
in §3 also produces β0=0.035, not 0.048.

**Resolution:** §3's parameter table now reads β0=0.035. Every user-facing and
internal reference to baseline growth is updated to match (§5's plain-language table:
"about 3.5% a month", not "about 5%"; §8 assumption 4: "~3.5%/month compounds to
~51%/year", not "~5%/month... ~80%/year"). `src/model.py::fit_model` derives β0 live
from the data, so this is a documentation fix, not a code change — the code was
already correct.

**Impact:** the default value shown in the "Revenue growth per month without extra
marketing" control (§6) is lower than originally documented. Since baseline growth
compounds over a 12-month horizon, this measurably lowers the default forecast total
versus what §3/§8 implied — worth knowing when eyeballing headline numbers against the
old draft spec, but it does not change the chosen model specification, the guardrails,
or any other decision in the frozen spec.
