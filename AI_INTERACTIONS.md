# AI interactions

Curated, annotated record of the AI's role in specifying and building this
tool. Structured in three parts: the modelling debate (Specification), the
build itself (Build), and the moments the user overrode the AI's judgment
(Overrides). Specification and build were two separate phases with two
separate tools: the specification below was done in a chat interface with
Claude Opus 4.6, using code execution for statistical verification, over
roughly two hours before any application code was written; the build that
follows was done in Claude Code, working from the frozen decision record
that specification phase produced (`CLAUDE.md`).

## Table of contents

**Override moments** — where the user overrode the AI's judgment, listed
first since these are the highest-signal entries in this document:

- [β0 transcription error](#β0-transcription-error) — a wrong diagnosis of
  the spec's own numbers, corrected by the user re-deriving them
- [Stale live-server verification gap](#stale-live-server-verification-gap)
  — "verified" was true of the source, false of the running app
- [Draft/saved split broke live-edit propagation to visuals](#draftsaved-split-broke-live-edit-propagation-to-visuals)
  — three of four visuals silently ignored the thing being edited
- [Visual 4 scope: aggregate per-scenario decomposition, not monthly](#visual-4-scope-aggregate-per-scenario-decomposition-not-monthly)
  — overridden from a monthly to a per-scenario view
- [Build order: risk-first over dependency-first](#build-order-risk-first-over-dependency-first)
  — overridden from a bottom-up dependency order

**Specification** (§1–12) — the modelling debate, chat interface, before
any code existed. **Build** — the checkpoint-by-checkpoint build, including
the bugs and gaps the override moments above are drawn from in more
detail. Both sections keep their numbered/named entries below, in the
order they happened.

---

## Specification

### 1. Reading the brief

Opened by asking for an interpretation of the exercise from a senior
engineer's perspective, before any data was shared.

The useful output was not a task list but a reframing: the brief is
deliberately under-specified, there is no correct model hidden in the
data, and the 2–3 hour cap is part of the test. What is being assessed is
whether a vague stakeholder request can be turned into a usable artifact
within a fixed budget, with assumptions made explicit.

**Decision:** treat documented assumptions and the AI-interactions
document as graded deliverables, not boilerplate.

### 2. First analysis was speculative — and wrong

Before the dataset was attached, the discussion covered adstock,
saturation curves, seasonality, and cohort-level LTV.

The dataset arrived: 21 rows, three columns. Most of that was not
estimable. Twelve seasonal terms cannot be fitted to 21 observations;
there is no channel split; there are no cohorts.

**Recorded because it is the honest shape of the process.** The first
plausible answer was built on assumptions about data that did not hold.
The correction came from loading the file, not from more reasoning.

### 3. The collinearity finding

Asked for a review of an appropriate simple model, with the data in hand.
Rather than proposing one, the analysis ran competing specifications and
compared them.

| Specification | Spend coefficient | R² |
|---|---|---|
| `revenue ~ spend` | 5.07 (p<0.001) | 0.969 |
| `revenue ~ spend + trend` | 1.24 (p=0.10, n.s.) | 0.988 |
| `revenue ~ trend` only | — | 0.986 |
| `log(rev) ~ log(spend)` | elasticity 1.49 | 0.976 |
| `log(rev) ~ log(spend) + trend` | elasticity 0.21 | 0.998 |

Spend correlates with revenue at 0.984; time correlates with revenue at
0.993 and with spend at 0.983. VIF ≈ 30. Adding a trend collapses the
marketing coefficient by 75% and removes its significance. A trend alone
explains 98.6% of variance.

Corroborating: ROAS rises monotonically from 2.71 to 4.16 while spend
nearly doubles. Improving efficiency at increasing scale is not how paid
acquisition behaves.

**This is the central finding of the exercise.** The obvious model implies
€5.07 return on every marginal euro, forever. It is attributing organic
growth to marketing, and a tool built on it would systematically encourage
over-spending.

### 4. A claim reversed by testing

The initial position was that carryover could not be identified from 21
observations. Testing contradicted it:

| Term | Coefficient | p-value |
|---|---|---|
| Δspend, current month | 0.301 | 0.0007 |
| Δspend, prior month | 0.208 | 0.0127 |

Adjusted R² rose from 0.252 to 0.471, and the two-term model won a
rolling-origin backtest out of sample (0.82% vs 0.99% MAPE). The
Durbin–Watson statistic on the single-term model had already been hinting
at an omitted lag.

**Decision:** include the carryover term. The stated impossibility was
wrong, and running the regression was what established it.

### 5. Specification chosen and alternatives rejected

`Δlog(revenue) = β₀ + β₁·Δlog(spend) + β₂·Δlog(spend)ₜ₋₁`

Rolling-origin, one-step-ahead, expanding window:

| Specification | Mean MAPE |
|---|---|
| **Growth + carryover (chosen)** | **0.82%** |
| Growth, contemporaneous only | 0.99% |
| log-log + trend | 1.60% |
| Trend only | 3.68% |
| Random walk | 4.72% |
| `revenue ~ spend` | 5.27% |

The defensible specification is also the most accurate. Bootstrap on the
elasticity (5,000 reps): mean 0.19, 95% interval [0.09, 0.33], P(β<0) =
0.002.

Rejected, with reasons:

- **Geometric adstock with fitted decay** — grid search peaked at λ≈0.40
  but was flat between 0.30 and 0.55. Weakly identified; the unconstrained
  two-lag form avoids committing to a decay rate the data cannot support.
- **Saturation / Hill curves** — ROAS rises monotonically with no
  inflection. There is no diminishing-returns signal to fit. Fitting one
  would invent a parameter. Handled with an out-of-range warning instead.
- **Seasonality** — not estimable from 21 months, and no December spike is
  present.
- **Any ML model** — 20 observations, one feature, and the output must be
  explainable to a CFO.

### 6. Industry tooling reviewed, then declined

Reviewed the current marketing-mix modelling landscape: Google Meridian
(Bayesian, TensorFlow Probability, replaced LightweightMMM, added a
Scenario Planner interface in 2026), Meta Robyn (Ridge with evolutionary
hyperparameter search), and PyMC-Marketing (fully Bayesian, Python-native).
The consensus framing is a layered stack — attribution for granularity,
MMM for privacy-safe aggregate measurement, incrementality experiments as
the calibration layer.

All three assume multiple channels and roughly two years of weekly data.
With 21 monthly points and one undifferentiated spend column, a Bayesian
MMM would be prior-dominated and would mean shipping a multi-gigabyte
image to serve a two-parameter regression.

**Decision:** name them in the README and explain the rejection. Knowing a
tool exists and choosing not to use it was judged the stronger signal.

### 7. Uplift semantics — a business decision, not a modelling one

The brief does not say whether an uplift persists or is a single-month
spike. In a compounding model these diverge sharply. A single +15% uplift
in month 3 of a 12-month horizon:

| Mode | 12-month total | vs baseline |
|---|---|---|
| One-month spike | €275.9M | +1.1% |
| Permanent lift | €308.3M | +13.0% |

Twelve times the incremental revenue from identical input.

**Decision:** expose both as a user control defaulting to permanent. A
tool that picks silently is making a strategic call that belongs to the
VP. Implementing the toggle also forces the correct data structure —
without separating the compounding base from the displayed value,
one-month uplifts silently compound and corrupt every downstream number.

Decaying uplifts are the realistic middle case and were left out of scope,
documented so that a permanent uplift reads as an upper bound.

### 8. Scope held against creep

Explicitly declined, and recorded so the omissions read as decisions:
budget optimizer, Monte Carlo simulation, multi-channel modelling,
sensitivity analysis, user accounts, database persistence, decaying
uplifts, configurable horizons.

The brief asked for exploration and comparison, not optimization.

### 9. AI in the process, not in the product

Considered adding a generated plain-English scenario summary. Declined: it
needs an API key that cannot live in a public repo, it adds latency and a
failure mode to a tool whose value is instant response, and the brief asks
for AI in the *process* of building the solution, not inside it.

The forecasting logic is a transparent statistical model chosen for
auditability. The VP must be able to explain any number to a CFO.

### 10. Non-technical usability as a hard constraint

Three constraints introduced during specification, all treated as
requirements rather than polish:

- **No statistical vocabulary anywhere user-facing.** Banned: elasticity,
  coefficient, p-value, confidence interval, adstock, carryover,
  regression, MAPE, R², bootstrap, significance. Enforced structurally by
  routing every user-facing string through `src/copy.py`, making the rule
  auditable in one file.
- **A guided first run.** The app opens with three scenarios already built
  and a dismissible welcome panel explaining what is on screen —
  explaining something visible rather than touring empty inputs.
- **One-click launch.** Terminal commands were ruled unacceptable for the
  end user.

### 11. Deployment: a conflict in the brief, and a pivot

The brief asks for Docker *and* the stakeholder cannot use a terminal.
These cannot both be satisfied by a single local artifact.

Resolution: containers run on servers. The VP opens a URL; the container
runs remotely. Initial plan was Hugging Face Spaces with the Docker SDK,
so one image would serve both the VP and the evaluators.

That plan failed on a free-tier concurrency quota. Pivoted to Streamlit
Community Cloud, which containerizes from `requirements.txt`. The
Dockerfile was retained for local reproducibility and to satisfy the
brief's stated preference.

Three launch paths documented: hosted link (VP), `docker run`
(evaluators), and `run.bat` / `run.sh` (anyone with Python).

### 12. Process design

Decisions about how the build itself would be run:

- **Separate deciding from building.** All modelling and scoping settled
  in chat, then frozen into a decision record dropped into the repo as
  `CLAUDE.md` so the agent read the spec rather than re-deriving it.
- **Risk-first build order.** Overrode the agent's proposed dependency
  order to put `model.py` first — it carries the project risk and is the
  only module with meaningful tests.
- **Hard gates at checkpoints.** Verification required before proceeding.
  This is what caught the β₀ transcription error; a fully autonomous run
  would have accepted the agent's plausible but incorrect explanation and
  inflated every forecast by 25 percentage points of annual growth.
- **Manual review at every visual.** No test can determine whether a
  non-technical stakeholder understands a screen. Manual review caught
  three defects the passing test suite did not: a frozen chart that
  ignored budget edits, unlabelled units, and an invisible line colour.

---

## Build

### Verification recovery

Across checkpoint 5's first two visuals, completion was reported twice on
verification that hadn't run against the thing being verified: a stale
live server behind an `AppTest` that only ever saw correct files (see
Overrides), then a chart that rendered but never received the live draft
(see Overrides) — the second miss for a different reason than the first,
since that `AppTest` checked "does it render," never "does it react to a
changed input."

After the second miss, the response changed in kind. Rather than
substitute another `AppTest` run for what the user asked for ("not
AppTest — a real interaction"), it named the actual limitation (no browser
automation in this session) and built a genuinely different check instead:
chart-building logic extracted into a Streamlit-free module (`src/charts.py`)
so a pytest test could call the real production function and assert its
output actually differs across inputs, then proved that test wasn't
vacuous by breaking the fix and confirming it failed before reverting.

This is where the verification practice changed for the rest of the
build: every new regression test from here on is mutation-checked —
break it, confirm the test fails, revert, confirm the suite is clean
again — before being reported as protecting against that class of bug.
Done again for the visual-4 decomposition-sum test (see Overrides).

### Excel export: raw numbers, not the on-screen formatted strings

The on-screen comparison table displays pre-formatted text ("€262.6M",
"+7.3%") per section 5's plain-language rule. The Excel export reuses the
same column headers but writes the underlying numeric values instead
(revenue/spend as floats, the baseline delta as a percentage number, not a
formatted string) -- a deliberate divergence from "what you see is what you
export." Reasoning: section 6 states her next action is "pasting numbers
into a deck," which implies she can sum, chart, or reformat the figures in
Excel; exporting pre-formatted text strings like "€262.6M" into spreadsheet
cells would block that. Verified the round trip actually produces numeric
(not text) columns, not just that the file opens.

### Palette assumed a light background

After all four checkpoint-5 visuals were built, the user reported the
draft's line colour (`#111827`, near-black) was invisible against Streamlit's
default dark theme. The AI had only ever looked at the app under its own
light-mode assumption and never checked a dark render.

Root cause was broader than one hex: every chart colour across all four
visuals (`SCENARIO_COLORS`, the segment colours, the history line, a
hardcoded `"white"` marker outline) had been picked by eye against a light
background, and Streamlit follows each viewer's OS/browser preference by
default -- so the same app renders light for some reviewers and dark for
others, and nothing had been checked against the dark case at all.

Fix: loaded the `dataviz` skill for its validated categorical palette
(CVD-safe, contrast-checked on both light and dark reference surfaces)
rather than hand-picking replacement hex values the same way the original
colours were picked. No JS runtime was available to run the skill's own
validator, so the draft colour and the app's own additions were
contrast-checked directly via the WCAG luminance formula in Python
instead. Moved every chart colour into a new `src/theme.py`, and pinned
an explicit dark theme in `.streamlit/config.toml` -- both requested by name.

Pinning the theme isn't just tidiness: computed contrast shows white at
17.4:1 on the dark surface but only 1.03:1 on a light one -- no single
flat colour reads on both a near-black and a near-white surface, so
"reads on both themes" is only true because the pin ensures just one
surface ever renders. Dark was chosen because the user's own fix language
("near-white or a bright neutral") only makes sense if dark is the pinned
surface -- inferred, not confirmed, and stated as such. Residual gap: a
viewer can still manually flip themes via Streamlit's own Settings menu,
with no server-side way to prevent it.

A follow-up correction: the driver chart's "base business" segment was
initially given a very light warm grey (`#c3c2b7`, 9.72:1 contrast) that
read as functionally white next to the draft's actual white line -- fixed
to a genuinely mid-toned slate (`#767570`, 3.77:1) so the largest, least
interesting segment stays visually recessive and doesn't compete with the
draft line or the two saturated, signal-carrying segments beside it.

### Stakeholder UI review before checkpoint 6

Before starting the tutorial and export, the user asked for a presentation-
only review of the app as it stood for a non-technical stakeholder, with an
explicit instruction not to implement any of it -- list findings, ranked by
impact, and let the user pick. The review was grounded in the app's actual
rendered output (pulled via `AppTest` -- widget labels, help text, table
contents) rather than a re-read of the source, which surfaced two things a
code read alone would have missed: a hardcoded `"Apply"` button string that
had slipped past every previous audit of the no-hardcoded-strings rule, and
a signed-zero formatting artifact (`+0.0%` vs `-0.0%` for two scenarios with
identical budgets) caused by floating-point noise between two independently
computed paths landing a few cents apart. Both were accepted and fixed at
checkpoint 8 (see below); the other nine findings were left for the user to
pick from later.

### Checkpoint 8: banned-vocabulary audit and two accepted UI fixes

Grepped `copy.py`, `app.py`, `src/charts.py`, and `src/theme.py` for
section 5's banned vocabulary (elasticity, coefficient, p-value,
confidence interval, adstock, carryover, regression, MAPE, R-squared,
bootstrap, significance, log) -- the only hits were in `copy.py`'s own
module docstring listing the banned words themselves, not in any actual
string value. Clean.

Implemented the two UI-review findings the user accepted: moved the
hardcoded `"Apply"` button string into `copy.py` as
`BUDGET_SCALE_APPLY_BUTTON`, and fixed `format_percent`'s signed-zero
artifact by special-casing "-0.0%" to "+0.0%" -- rounding to zero now
always displays as positive regardless of which side of zero the
underlying float landed on. Both presentation-only, per the review's own
scope; the signed-zero fix was mutation-checked.

### Checkpoint 7: a requirements.txt pin that had never actually been tested

`requirements.txt` had been version-pinned since before this build began,
but every local test run in this session used Python 3.14 (the only
interpreter on the development machine), which cannot get wheels for the
originally pinned `pandas`/`numpy`, so local verification had silently
been running against newer, unpinned substitutes the whole time -- not
the versions the Dockerfile's `python:3.12-slim` would actually install.

Building the real image for the first time exposed this: `numpy==2.2.1`
(released after `statsmodels==0.14.4`) broke a `pandas.util._decorators`
compatibility path inside statsmodels, and an unpinned `scipy` resolved to
a version that had removed `scipy._lib._util._lazywhere`, which
statsmodels 0.14.4 imports. Neither failure was visible from the Python
3.14 dev venv, where newer versions of everything happened to still work
together. Root-caused empirically in throwaway containers (bisecting
versions, not reading changelogs); pinned `numpy==2.1.3` (contemporary
with statsmodels 0.14.4's release) and a new explicit `scipy==1.14.1`.
Rebuilt the image, ran the full suite inside the container, and booted it
to confirm the app serves -- the first time these exact pins had been
exercised end to end.

### Zero budget: a modelling boundary, not just an input gap

The user reported a zero budget crashing the app with `ZeroDivisionError`
in `check_guardrails` (a month-over-month percentage change computed as
`curr/prev - 1`, undefined when `prev` is zero). Fixing only that
division would have been treating this as an input-validation problem --
clamp the denominator, move on. The user's framing was more precise: "the
model uses Δlog(spend), so log(0) is undefined and fixing the division
will move the crash downstream." That's a claim about the *model*, not
the guardrail code -- the growth-rate-with-carryover specification
(`CLAUDE.md` §3) has no defined behaviour at zero spend, because its
entire mechanism is a log-difference, and `log(0)` is `-inf` by
definition, not an implementation oversight.

Reverting only the `check_guardrails` fix reproduced the exact reported
`ZeroDivisionError`. Reverting only the `model.py` fix reproduced a second,
independent failure that raised nothing at all: `log(0)` propagates as
`-inf`, then `nan`, silently corrupting every month *after* the zero one
-- arguably worse than a crash since nothing signals anything went wrong.
Both were real and stacked in the same code path; the second would have
shipped invisibly if the fix had stopped at the division.

Resolution treats zero as a boundary condition of the specification, not
noise to be validated away: any month-over-month transition touching a
zero (or negative) spend month has no defined marketing contribution, so
that transition contributes nothing beyond baseline growth -- an explicit
modelling decision (documented in `model.py`), not a silent clamp. Also
surfaced as a specific plain-language message (`copy.py`) distinct from
the generic "too small" guardrail, since zero isn't just an extreme value
on the same scale -- it's a different regime the model has nothing to say
about.

### Two features reported complete that did nothing

The user found two controls that rendered, accepted a click, and had zero
visible effect -- both had been reported as working in earlier checkpoints.

**"Show me an example."** The button existed, its click handler ran
without error, and it genuinely added something to `st.session_state.scenarios`
-- but as a new *saved* scenario, not a change to the draft the user was
looking at in the sidebar. The budget table stayed at zero, the initiatives
table stayed empty, and the panel closed immediately after the click, so
there was nothing left on screen to suggest anything had happened unless
you scrolled to the comparison table and recognised a new row. The AI's
original design in checkpoint 6 read section 7's "adds a demo scenario"
literally -- a new `Scenario` object -- without asking what a demo is *for*:
showing the mechanic in the controls the user would actually use, not
adding an entry to a table three scrolls down. Fixed by populating
`draft_budget` and `draft_uplifts_df` directly, the same session-state keys
the sidebar's own tables read from.

**Saved scenario budgets.** Conservative, Plan, and Aggressive drove the
forecast chart and comparison table from the first checkpoint they
appeared in, but nothing let a viewer see what any of them actually
contained -- the exact monthly figures existed only inside `Scenario`
objects in `st.session_state.scenarios`, never rendered anywhere. This
was not a regression; it was a capability that was never built, reported
as done because the *outputs* of those scenarios were visibly correct.
The user's framing: "she must be able to answer 'what is Aggressive
actually spending?' without guessing." Fixed with a scenario selector plus
a "Load" button that copies a saved scenario's budget and initiatives
into the same editable tables the draft uses (inspectable, and editable
without altering the saved version unless re-saved under the same name),
and a "Monthly budget" column added to the comparison table so the range
is visible without loading anything at all.

Both were caught by the user actually clicking the app, not by the test
suite: `AppTest` had already exercised both code paths and found nothing
wrong, because nothing asserted the *specific* place a demo/inspection
feature is supposed to put its result. New tests for both check state at
that exact location, mutation-checked.

---

## Overrides

### β0 transcription error

The frozen spec (`CLAUDE.md` §3) listed β0 = 0.048. When `tests/test_model.py`
was written and run against the fitted model, the recovered value was 0.035.

The AI offered three options and recommended logging the recomputed value in
`decisions.md`, attributing the gap to a pre-freeze snapshot of the dataset.
**That diagnosis was wrong.** The user re-derived the coefficient and found
the spec had mixed sources: β1 and β2 were taken from the two-lag
(growth-with-carryover) model, but β0 had been carried over from an earlier
single-term model — one where the absent carryover term inflates the
intercept. 0.035 was the correct value for the two-lag specification actually
being shipped.

Impact if undetected: baseline growth would have been overstated at roughly
76%/year instead of the correct ~51%/year, inflating every forecast the tool
produces. Caught because checkpoint 1 had a hard gate requiring the fitted
coefficients to match the spec before moving on.

### Stale live-server verification gap

While building checkpoint 5's headline metric cards, the AI edited `copy.py`
and `app.py`, ran `streamlit.testing.v1.AppTest` in a fresh subprocess (which
read the current files and passed with no exceptions), and reported the
checkpoint as "Verified via AppTest: no exceptions." The user then hit an
`AttributeError` on the actual running app at `localhost:8501` for a constant
that, per the files on disk, existed.

**Root cause:** the background Streamlit server had been running continuously
since checkpoint 4 and was never restarted after subsequent edits. Python
caches imported modules in `sys.modules` per process; Streamlit re-executes
`app.py`'s top level on every rerun, but `from src import copy` in an
already-running process rebinds to the cached module object rather than
re-reading the file. The live server was serving a stale, pre-edit `copy.py`
— which also explains why the section-5 currency-formatting fix (`"Marketing
budget (€M)"`) looked unfixed to the user, even though it was already correct
on disk. `AppTest`'s fresh subprocess never touched that stale state, so it
kept passing while the actual page the user was looking at was broken.

**Impact:** the AI's "verified" claim was true of the source files and false
as a claim about the running app — exactly the kind of gate the user said
they were relying on. Caught only because the user checked the live app
directly rather than trusting the report.

**Fix:** after any change to `src/*.py` or `app.py`, the AI now kills and
restarts the actual background server process, confirms a new PID, curls it
for liveness, and only then runs `AppTest` — so "verified" means the live
server was rebuilt from current disk state, not just that an isolated
subprocess happened to read the right files.

### Draft/saved split broke live-edit propagation to visuals

While building the forecast chart, the AI computed the live sidebar draft as
a separate `draft_result` object, wired it into the headline metric cards,
and left the chart, comparison table, and guardrail-scenario footnote
reading only from `st.session_state.scenarios` (the saved presets). Editing
the budget moved the headline cards but not the chart line, the comparison
table, or the guardrail marker on the draft -- three of four places a
scenario's numbers are shown silently ignored the thing the user was
actually editing.

**Caught by the user manually interacting with the running app, not by the
test suite** -- `AppTest` had already run clean against this exact code
(chart rendered, right trace count, no exceptions) because it only checked
structural presence, never that the chart responds to a changed input.
Fixed by computing one `all_results = saved_results + [draft_result]` list
every visual reads from, instead of three parallel readings of "the
current scenario." Verified with a different method deliberately:
`src/charts.py`'s logic extracted into a Streamlit-free module so a real
pytest test could call it with two different draft budgets and assert the
output actually differs -- a data-flow check, not another
structural-presence pass.

### Visual 4 scope: aggregate per-scenario decomposition, not monthly

For the revenue-driver chart (section 6, item 4 — "the chart that carries
the model's central finding"), the AI recommended decomposing a single
scenario's revenue month by month, reasoning that this most directly shows
the mechanism behind the model's central finding (base business dominates
every month). The user overrode this in favor of aggregate, per-scenario
decomposition — one stacked bar per scenario (Conservative/Plan/Aggressive/
draft), each split into the same three components, summed over the full 12
months.

**Reason:** the user is choosing between plans, so the chart must answer
"why does this one win" — the composition of the *difference* between
scenarios. Monthly composition explains the model's mechanism, which is a
concern for the analyst who built the model, not for the decision-maker
using it. The chosen version is also a natural extension of visual 3: same
scenarios, same ordering, now split into components instead of a single
total.

**Decomposition definitions used** (implemented in `run_scenario`,
`src/scenarios.py`, unchanged by this override — only the chart's
aggregation level changed):

- **Base business** — baseline growth compounding from the last actual
  month, with a flat budget held at the last observed level and no
  initiatives.
- **From marketing** — the difference between the scenario's actual budget
  path and that flat-budget counterfactual, initiatives excluded.
- **From initiatives** — the uplift contribution on top.

The three are guaranteed to sum to the scenario's total revenue by
construction (each is a running difference against the next). Tested for
Conservative, Plan, Aggressive, and a draft carrying an uplift in
`tests/test_scenarios.py::test_decomposition_sums_to_total_for_every_default_scenario`
and at the chart-trace level in
`tests/test_charts.py::test_driver_chart_segments_sum_to_scenario_totals`;
both were mutation-checked (see Verification recovery, above).

### Build order: risk-first over dependency-first

The AI proposed a bottom-up build order by dependency: `copy.py` →
`formatting.py` → `model.py` → `scenarios.py` → `app.py`. The user overrode
this in favor of `model.py` first: it carries the project's risk, it's the
only module with meaningful tests, and writing `copy.py` before the UI exists
means writing its string surface area speculatively. Risk-first beats
dependency-first under a time box.
