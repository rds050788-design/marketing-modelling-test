# Revenue Scenario Planner — Decision Record

Frozen spec. Written before any code. Decisions here are settled; do not re-litigate
them mid-build. If something must change, note it in `decisions.md` with a reason.

This file also serves as `CLAUDE.md` in the repo root.

---

## 1. The brief

Central Analytics is building a forecasting tool for the VP of Product of one of our
games. She needs to:

- forecast monthly revenue from a planned marketing budget
- enter different marketing budgets
- apply expected revenue uplifts to selected months, representing planned game
  initiatives
- compare scenarios and pick one

Input: `dataset.csv`. Deliverables: README, a document of AI interactions, source code.
A Python web app, containerized with Docker, is recommended. Recommended effort:
2–3 hours.

**The user is a non-technical marketing/product executive.** Every user-facing
decision defers to that.

---

## 2. What is in the data

21 monthly rows, Nov 2024 → Jul 2026. Three columns: `year_month`,
`mkt_investment`, `total_revenue`. No channel split, no installs, no DAU, no cohorts.

| Fact | Value |
|---|---|
| Observations | 21 |
| Spend range | €2.23M – €4.38M (1.96×) |
| Month-over-month spend change | −4.8% to +18.5% |
| Revenue growth, mean MoM | +5.4% |
| ROAS, first 5 months → last 5 months | 2.91 → 3.87 |
| Revenue rose month-on-month | 21 of 21 months |

---

## 3. The modelling decision

### The trap

Spend correlates with revenue at 0.984. Time correlates with revenue at 0.993 and
with spend at 0.983. Marketing effect and organic trend are nearly perfectly
confounded (VIF ≈ 30).

| Specification | Spend coefficient | R² |
|---|---|---|
| `revenue ~ spend` | 5.07 (p<0.001) | 0.969 |
| `revenue ~ spend + trend` | 1.24 (p=0.10, **not significant**) | 0.988 |
| `revenue ~ trend` only | — | 0.986 |
| `log(rev) ~ log(spend)` | elasticity 1.49 | 0.976 |
| `log(rev) ~ log(spend) + trend` | elasticity 0.21 | 0.998 |

Adding a trend collapses the marketing coefficient by 75% and kills its significance.
A trend alone explains 98.6% of variance. The naive model implies €5.07 return on
every marginal €1 of marketing, forever — it is attributing organic growth to
marketing, and it would lead the VP to over-spend.

Corroborating evidence: ROAS rises monotonically from 2.71 to 4.16 while spend nearly
doubles. Improving efficiency at increasing scale is not how paid acquisition behaves;
it is the signature of a product whose growth is not primarily bought.

### Chosen specification

Model in growth rates. Differencing detrends both series and breaks the confound.

```
Δlog(revenue)_t = β0 + β1·Δlog(spend)_t + β2·Δlog(spend)_{t-1} + ε_t
```

| Parameter | Fitted | p-value | Meaning |
|---|---|---|---|
| β0 | 0.035 | — | baseline monthly growth, no extra marketing |
| β1 | 0.301 | 0.0007 | same-month response to spend change |
| β2 | 0.208 | 0.0127 | following-month carryover |

Adjusted R² 0.471, versus 0.252 without the carryover term. Bootstrap on the
single-term elasticity (5,000 reps): mean 0.19, 95% interval [0.09, 0.33],
P(β<0) = 0.002. The effect is real, small, and bounded well away from 5.07.

### Backtest

Rolling-origin, one-step-ahead, expanding window.

| Specification | Mean MAPE |
|---|---|
| **Growth + carryover (chosen)** | **0.82%** |
| Growth, contemporaneous only | 0.99% |
| log-log + trend | 1.60% |
| Trend only | 3.68% |
| Random walk | 4.72% |
| `revenue ~ spend` | 5.27% |

The defensible specification is also the most accurate. It beats a random walk by
roughly 5×.

### Rejected

- **`revenue ~ spend`** — confounded, over-states marketing by an order of magnitude.
- **Geometric adstock with fitted decay λ** — grid search peaked at λ≈0.40 (long-run
  elasticity 0.42) but the surface was flat between 0.30 and 0.55. Weakly identified.
  Using the unconstrained two-lag form instead avoids committing to a decay rate the
  data cannot pin down. Mention in the README, do not implement.
- **Saturation / Hill curves** — ROAS rises monotonically with no inflection across the
  whole sample. There is no diminishing-returns signal to fit. Fitting one would be
  inventing a parameter. Handled as a guardrail instead (see §6).
- **Seasonality** — 21 months cannot support 12 monthly terms, and there is no December
  spike in the data.
- **Any ML model** — 20 observations, one feature; and the VP must be able to explain
  the number to a CFO.
- **Meridian / Robyn / PyMC-Marketing** — the right tools at production scale. All
  assume multiple channels and ~2 years of weekly data. With 21 monthly points and one
  undifferentiated spend column a Bayesian MMM would be prior-dominated, and it would
  mean shipping a multi-GB image to serve a two-parameter regression. Named and
  explicitly rejected in the README.

---

## 4. Uplift semantics

Uplifts represent business knowledge the model cannot have — a battle pass, a seasonal
event. They are applied **on top of** the fitted model, never mixed into it:

```
forecast = model(budget) × (1 + uplift)
```

Each uplift carries a mode:

- **Permanent lift to the revenue base** (default) — raises the compounding base, so
  later months build on the higher level.
- **One-month spike** — affects only that month; the underlying base is untouched.

This requires tracking two series: an internal `base` that only permanent uplifts
modify, and a `displayed` value that applies one-month spikes cosmetically. Skipping
this makes one-off uplifts silently compound and corrupts every downstream number.

The two modes are not a rounding difference. A single +15% uplift in month 3 of a
12-month horizon:

| Mode | 12-month total | vs baseline |
|---|---|---|
| One-month spike | €275.9M | +1.1% |
| Permanent lift | €308.3M | +13.0% |

Twelve times the incremental revenue from the same input. This is a business judgment,
not a modelling one, so it belongs to the user as an explicit control.

Decaying uplifts are the realistic middle case and are **out of scope**. Documented as
a known simplification: a permanent uplift should be read as an upper bound on a
sustained initiative.

---

## 5. Plain-language rule

**No statistical vocabulary appears anywhere the user can see.** Banned from the UI:
elasticity, coefficient, p-value, confidence interval, adstock, carryover, log,
regression, MAPE, R², bootstrap, significance. These live in one collapsed
"How this works" section and in the README.

| Internal | User-facing wording |
|---|---|
| Elasticity 0.19 | "Every 10% more marketing adds roughly 2% more revenue that month" |
| Baseline growth 3.5% | "Revenue grows about 3.5% a month on its own, without extra marketing" |
| Lagged spend term | "Marketing keeps working into the following month" |
| 90% bootstrap interval | "Likely range" |
| Backtest MAPE 0.82% | "Tested against the last 8 months, forecasts landed within about 1%" |
| Outside observed spend range | "This budget is far larger than anything tried before — treat with caution" |
| Permanent uplift | "Permanent lift to the revenue base" |
| One-off uplift | "One-month spike" |

Formatting: currency as `€18.2M`, never `18164515.32`. Dates as `Nov 2026`, never
`2026-11`. Sentence case throughout. No jargon in tooltips either.

---

## 6. Application spec

### Layout

Left sidebar — inputs. Main panel — outputs, in this order:

1. **Headline metrics** (4 cards): total 12-month revenue, total marketing spend,
   revenue per €1 spent, change vs the baseline scenario.
2. **Revenue forecast chart**: history solid, forecast dashed, shaded likely range,
   one colour per scenario. Uplift months flagged with a marker carrying the user's
   own note text.
3. **Compare scenarios**: horizontal or vertical bars, total revenue per scenario.
4. **Where revenue comes from**: stacked bar splitting forecast revenue into base
   business, from marketing, and from initiatives. This is the chart that carries
   the model's central finding visually and must not be cut.

### Sidebar controls

- **Marketing budget** — editable per-month table, 12-month horizon, pre-filled with a
  sensible default. Plus a shortcut to scale the whole vector by a percentage.
- **Game initiatives** — `st.data_editor` table: Month | Uplift % | Mode | Note.
  Mode is a two-option selector reading "Permanent lift to the revenue base" /
  "One-month spike", defaulting to permanent. Note is free text, e.g.
  "Battle pass launch", and surfaces on the chart and in the comparison.
- **Baseline growth** — editable, defaulting to the fitted value, labelled
  "Revenue growth per month without extra marketing". This is the single largest
  driver of the forecast and it is not identified by marketing at all, so the user
  must be able to challenge it. Visible in the sidebar, not buried.
- **Save scenario** — name it, add to comparison.

### Guardrails

- Warn whenever a scenario's spend leaves €2.23M–€4.38M, or a month-over-month change
  leaves −4.8%…+18.5%. Plain wording, amber, non-blocking.
- Always show the likely range, never a bare point estimate.

### Pre-seeded state

The app opens with three scenarios already built — Conservative, Plan, Aggressive —
and the chart already drawn. Nobody should meet an empty state.

### Export

Download comparison as Excel. Her next action is pasting numbers into a deck.

---

## 7. First-run tutorial

Native Streamlit, `st.session_state`, no dependencies.

**Welcome panel**, shown on first load, dismissible, reopenable via a `?` in the
header. Four steps, each one sentence, each pointing at something already on screen —
it explains the pre-seeded scenarios rather than touring empty inputs.

> **This tool forecasts revenue for the next 12 months.**
> 1. Three example scenarios are already loaded. The chart compares them.
> 2. Change the marketing budget in the table on the left — type any monthly figure.
> 3. Add a game initiative and choose whether it permanently lifts revenue or is a
>    one-month spike.
> 4. Save it as a new scenario to compare against the others.
>
> [Got it] [Show me an example]

"Show me an example" adds a demo scenario with a battle-pass uplift pre-filled, so the
mechanic is visible without typing.

**Tooltips** via `help=` on every control. One plain sentence each.

Session state resets on refresh, so the panel reappears for a returning visitor. This
is acceptable and not worth engineering around. Note it in the README.

---

## 8. Assumptions to document

1. Revenue is assumed net of platform fees. Currency assumed EUR.
2. Spend is a single undifferentiated marketing figure; no channel attribution.
3. Marketing effect is estimated from month-to-month variation, not from an
   incrementality experiment. This is correlation under a detrending assumption, not
   proven causation.
4. Baseline growth is assumed to continue at the fitted rate. It is user-adjustable
   because ~3.5%/month compounds to ~51%/year, which is a strong assumption over a
   12-month horizon.
5. No seasonality is modelled — not estimable from 21 months, and no December spike
   is present in the data.
6. No saturation is modelled — the data shows no diminishing returns. Handled with an
   out-of-range warning instead.
7. Uplifts are user-supplied business judgment, applied outside the fitted model.
8. Uplifts are permanent or single-month; decay is not modelled.
9. Forecast horizon fixed at 12 months.
10. The dataset is synthetic and treated as such (see §10).

### What I would do with more time

Geo holdout or spend-variation experiments to identify marketing effect causally —
the honest conclusion is that this data cannot cleanly separate marketing from trend,
and the fix is experimental design, not a fancier regression. Then a proper MMM once
channel-level weekly data exists.

---

## 9. Delivery

One container, two audiences.

| Audience | Action | Runs |
|---|---|---|
| VP of Product | Clicks a URL | The container, on hosted infra |
| Interview panel | `docker build && docker run` | The same container, locally |

Hosted on Hugging Face Spaces with the **Docker SDK** — which is now the documented
path for Streamlit there, since the built-in Streamlit SDK is deprecated. Free CPU
tier, no CLI required.

Platform constraints, baked in from the first commit:

- Port **7860**, not Streamlit's 8501. Set `app_port: 7860` in README frontmatter.
- Run as **UID 1000** — Spaces execute the container as that user.
- `--server.headless=true --server.address=0.0.0.0`.
- README needs YAML frontmatter with `sdk: docker`.
- Idle Spaces sleep; first visit after a quiet period takes ~1 minute. Note in README.

```dockerfile
FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .
USER user
EXPOSE 7860
CMD ["streamlit", "run", "app.py", "--server.port=7860", \
     "--server.address=0.0.0.0", "--server.headless=true"]
```

**Deploy a hello-world stub before building any features.** Confirm the URL loads at
the ~20 minute mark. Never debug deployment at the end of a time budget.

---

## 10. Production note for the README

## 10. Deployment note for the README

> The dataset provided is synthetic, so the tool is deployed to Streamlit
> Community Cloud for evaluation convenience — the VP opens a link, no
> installation required. Three launch paths are available:
>
> | Audience | Action | Requirement |
> |---|---|---|
> | VP of Product | Opens the hosted link | None |
> | Interview panel | `docker build && docker run` | Docker |
> | Anyone with Python | Double-click `run.bat` / `run.sh` | Python 3.12 |
>
> The application is containerized (see `Dockerfile`). Streamlit Community
> Cloud performs its own containerization from `requirements.txt`, so the
> hosted app and the local container are built from the same pinned
> dependency set.
>
> In production the same application would run on internal infrastructure:
> a private container service inside the company VPC (ECS/Fargate, Cloud Run
> with internal ingress, or an internal Kubernetes namespace), behind SSO,
> with no public ingress. Revenue and marketing spend are commercially
> sensitive and would not leave the corporate network. Free public hosting
> is an evaluation convenience, not a deployment recommendation. The
> application layer is unchanged — that is the point of containerizing it.
> What changes is the registry, the ingress rules, and an auth proxy.
>
> Historical data would be read from the warehouse rather than a bundled CSV,
> the model refit on a monthly cadence as actuals land, and saved scenarios
> persisted to a database rather than session state.

Hosting notes: the free tier requires a public GitHub repository and provides
roughly 1 GB of memory (ample for 21 rows and a two-parameter regression).
Apps sleep after 12 hours without traffic, so the first visit after a quiet
period takes about a minute to wake. Mention this in the README so a slow
first load is not mistaken for a broken app.

---

## 11. Out of scope

Stated explicitly so the omissions read as decisions: budget optimizer, Monte Carlo
simulation, multi-channel modelling, sensitivity analysis, user accounts, persistence
beyond session state, decaying uplifts, horizons other than 12 months.

The brief asked for exploration and comparison, not optimization.

---

## 12. Stack

| Layer | Choice | Why |
|---|---|---|
| Modelling | `statsmodels` OLS | p-values, intervals, diagnostics — the inference is the argument |
| Data | `pandas`, `numpy` | 21 rows |
| Intervals | Residual bootstrap, hand-rolled | ~15 lines, no dependency |
| UI | Streamlit | Sidebar/table/chart maps onto the four required capabilities |
| Charts | Plotly | Interactive, annotatable, scenario overlay |
| Export | `openpyxl` | Excel download |
| Tests | `pytest` | Assert fitted coefficients and backtest MAPE |
| Container | `python:3.12-slim` | Small image, fast build |

No scikit-learn, no Prophet, no PyMC. Every dependency justified in one line.

---

## 13. Repo structure

```
README.md hosted link first, then Docker, then run scripts, then assumptions
AI_INTERACTIONS.md curated prompts and where the AI was overridden
decisions.md anything changed after this record was frozen
requirements.txt pinned
Dockerfile port 8501
.gitignore must NOT ignore data/dataset.csv
.dockerignore excludes .git, .venv, caches — keeps tests/ in the image
run.bat Windows: venv + install + launch + open browser
run.sh macOS/Linux: same
app.py Streamlit UI only
src/
model.py fit, forecast, bootstrap (~60 lines)
scenarios.py scenario objects, uplift application, comparison metrics
formatting.py currency, dates, number formatting
copy.py all user-facing text in one place
data/dataset.csv must be committed — the hosted build reads it from the repo
tests/test_model.py
```


`copy.py` exists so the plain-language rule (§5) is auditable in one file
rather than scattered through the UI.

`data/dataset.csv` is committed deliberately. Streamlit Community Cloud builds
from the repository, so an ignored CSV produces a `FileNotFoundError` visible
only in the deploy log.

`tests/` is deliberately kept in the Docker image so the panel can run
`docker run --entrypoint pytest <image>` and verify the fitted coefficients
and backtest figures from §3 inside the container.

---

## 14. Engineering practices

Do: module separation as above, type hints, docstrings, pinned requirements, 4–6
pytest tests asserting coefficients and backtest MAPE, `.gitignore`, meaningful commit
history.

Skip: CI pipelines, pre-commit hooks, coverage badges, Makefiles, lockfile tooling,
logging frameworks, config management. On an exercise this size they read as ceremony
rather than rigour.

Commit history matters more than usual here — it is independent evidence of process
alongside `AI_INTERACTIONS.md`.

---

## 15. Deliverables checklist

- [ ] `README.md` — AI models and tools used; how to run locally; assumptions; how to
      use the tool
- [ ] `AI_INTERACTIONS.md` — curated, annotated, with override moments called out
- [ ] Source code
- [ ] Live URL
- [ ] Dockerfile that builds and runs clean from a fresh clone
