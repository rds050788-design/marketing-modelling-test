# AI interactions

Curated, annotated record of the AI's role in specifying and building this
tool. Structured in three parts: the modelling debate (Specification), the
build itself (Build), and the moments the user overrode the AI's judgment
(Overrides).

---

## Specification

### Hosting pivot: Hugging Face Spaces to Streamlit Community Cloud

The original plan was Hugging Face Spaces with the Docker SDK, so a single
container would serve both the VP of Product and the interview panel. This
hit the free tier's concurrency quota. The deployment pivoted to Streamlit
Community Cloud, which containerizes directly from `requirements.txt`. The
Dockerfile was retained for local reproducibility and to satisfy the brief's
containerization requirement. Three launch paths are documented: the hosted
link, `docker build && docker run`, and `run.bat` / `run.sh`.

---

## Build

_Entries are added at each remaining checkpoint, covering anything the user
corrected or any decision that could reasonably have gone another way._

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
(the chart rendered, had the right trace count, no exceptions) because it
only checked structural presence, never that the chart actually responds to
a changed input. Fixed by computing one `all_results = saved_results +
[draft_result]` list that every visual (chart, table, footnote) reads from,
so there is a single source of truth instead of three parallel readings
of "the current scenario." Verification for this fix used a different
method deliberately: `src/charts.py`'s chart-building logic was extracted
out of `app.py` into a Streamlit-free module specifically so a real pytest
test (`tests/test_charts.py`) could call it directly with two different
draft budgets and assert the resulting chart line actually differs --
proving the fix with a genuine data-flow check rather than another
structural-presence pass.

### Build order: risk-first over dependency-first

The AI proposed a bottom-up build order by dependency: `copy.py` →
`formatting.py` → `model.py` → `scenarios.py` → `app.py`. The user overrode
this in favor of `model.py` first: it carries the project's risk, it's the
only module with meaningful tests, and writing `copy.py` before the UI exists
means writing its string surface area speculatively. Risk-first beats
dependency-first under a time box.
