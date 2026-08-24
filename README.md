# Revenue Scenario Planner

A forecasting tool for a game's VP of Product: plan a marketing budget, add
planned initiatives, and compare scenarios before committing to one.

## Live link

**Not yet deployed.** Packaging, testing, and Docker verification are done
(see `AI_INTERACTIONS.md` and `decisions.md` for the current build status);
deployment to Streamlit Community Cloud is the one remaining step. This
line will be replaced with the hosted URL once it's live — see
[Deployment](#deployment-and-production-note) below for the plan.

## What this tool does

You give it a 12-month marketing budget and, optionally, a list of planned
game initiatives (a battle pass, a seasonal event). It forecasts monthly
revenue for that plan, shows a likely range around the forecast, and lets
you build several plans side by side to compare before picking one.

Three scenarios — Conservative, Plan, Aggressive — are pre-built on
launch, so there's something to look at immediately. The forecast is built
from a statistical model fit to your game's own 21 months of spend and
revenue history, not a rule of thumb.

## How to use it

**The tutorial:** a welcome panel walks through the basics the moment you
open the app. Click **Got it** once you've read it, or click **Show me an
example** to have it fill in a realistic budget and a pre-filled
battle-pass initiative for you, so you can see how everything works
without typing anything yourself. Click the **?** next to the title any
time afterward to bring the panel back.

1. **View or load a saved scenario** (top of the sidebar) — pick
   Conservative, Plan, or Aggressive and click **Load** to see exactly
   what budget and initiatives it contains in the tables below. This is
   how you check what a saved plan actually spends, not just its outcome.
2. **Marketing budget** — a 12-month table you can edit directly, plus a
   shortcut to scale the whole budget up or down by a percentage in one
   step. It starts blank; build it up one month at a time, or load a
   scenario first as a starting point.
3. **Revenue growth per month without extra marketing** — how fast your
   game grows on its own, with no extra marketing. This defaults to a
   fitted value but is deliberately yours to challenge — it's the single
   biggest lever on the 12-month total, and it isn't something marketing
   spend can tell you.
4. **Game initiatives** — add a row for anything you expect to move
   revenue beyond marketing: a month, a percentage, a note ("Battle pass
   launch"), and whether it's a **permanent lift** (revenue stays higher
   every month after) or a **one-month spike** (higher for that month
   only, then back to normal). This distinction matters a lot — the same
   +15% uplift is worth about 12× more over a year as a permanent lift
   than as a one-month spike, since a permanent lift compounds.
5. Watch the cards, the forecast chart, the comparison table, and the
   "where revenue comes from" chart update live as you edit. On the
   forecast chart, coloured dashed lines are your saved plans, each with a
   fixed budget; the white line is the plan you're currently editing, not
   yet saved.
6. **Save scenario** once you're happy with a plan, to add it to the
   comparison table permanently instead of it just being "current."
7. A warning icon (⚠) next to a scenario's name means its budget goes
   beyond anything ever tried in your game's history. On the forecast
   chart, the affected part of its line is shown dotted and lighter, with
   a wider likely range — hover over it to see why. Not a hard stop, just
   a flag that this part of the forecast is less certain than the rest.
8. **Download comparison as Excel** to take the numbers into a deck.

## How to run locally

### Docker, from a terminal

```bash
docker build -t revenue-scenario-planner .
docker run -p 8501:8501 revenue-scenario-planner
```

Then open http://localhost:8501.

To run the test suite inside the same image the app runs in:

```bash
docker run --rm --entrypoint pytest revenue-scenario-planner
```

### Docker, no terminal needed

The steps above assume comfort with a terminal. If that's not you, and the
hosted link above isn't available to you either, this does the same thing
with no commands to type:

1. Install **Docker Desktop** from [docker.com](https://www.docker.com/products/docker-desktop/)
   (free for personal use). Open it once after installing, so it's running
   in the background.
2. Open this project's folder.
3. Double-click **`run-docker.bat`** (Windows) or **`run-docker.sh`**
   (Mac) — on Mac you may need to right-click it and choose "Open" the
   first time.
4. Wait for the first build — it downloads and sets everything up, which
   takes a few minutes. Later runs are much faster.
5. Your browser opens automatically at http://localhost:8501 once the app
   is ready.

**This is not the recommended path.** The hosted link at the top of this
page needs none of the above — no installation, nothing to wait for. Use
this only if the hosted link isn't an option for you.

### Run scripts, no Docker

No Docker, no terminal commands to remember — these create a Python
virtual environment, install dependencies, and launch the app (which
opens your browser automatically). Requires Python 3.12.

- **Windows:** double-click `run.bat`
- **macOS/Linux:** `./run.sh`

## AI models and tools used

Specification and build were two separate phases, with two different
tools — the full curated log, including where the AI was wrong and where
the user overrode it, is in `AI_INTERACTIONS.md`.

- **Claude Opus 4.6**, chat interface with code execution for statistical
  verification — roughly two hours of specification work, before any
  application code was written. Ran the competing model specifications in
  §"The model, and why" below, produced the frozen decision record that
  became `CLAUDE.md`, and got a real claim (that carryover wasn't
  identifiable from 21 points) wrong before testing corrected it.
- **Claude Code** (Sonnet 5) — the build itself, working from that frozen
  spec through 11 checkpoints with hard verification gates at each one.
- The **data-viz skill** bundled with Claude Code — supplied the validated
  categorical colour palette the charts use, contrast-checked against the
  app's pinned dark theme.
- **pytest**, Streamlit's **`AppTest`**, and **Docker** as verification
  tools during the build — Docker in particular caught a real dependency
  incompatibility (`requirements.txt`'s pinned `statsmodels` version
  silently broken by an unpinned `scipy`/`numpy`) that had been invisible
  in local testing the whole build, because the development machine's
  Python version couldn't install the pinned packages and had silently
  been running newer substitutes instead.

## The model, and why

### The trap

Spend correlates with revenue at 0.984. Time correlates with revenue at
0.993 and with spend at 0.983. Marketing effect and organic trend are
nearly perfectly confounded (VIF ≈ 30).

| Specification | Spend coefficient | R² |
|---|---|---|
| `revenue ~ spend` | 5.07 (p<0.001) | 0.969 |
| `revenue ~ spend + trend` | 1.24 (p=0.10, **not significant**) | 0.988 |
| `revenue ~ trend` only | — | 0.986 |
| `log(rev) ~ log(spend)` | elasticity 1.49 | 0.976 |
| `log(rev) ~ log(spend) + trend` | elasticity 0.21 | 0.998 |

Adding a trend collapses the marketing coefficient by 75% and kills its
significance. A trend alone explains 98.6% of variance. The naive model
implies €5.07 return on every marginal €1 of marketing, forever — it is
attributing organic growth to marketing, and it would lead the VP to
over-spend.

Corroborating evidence: ROAS rises monotonically from 2.71 to 4.16 while
spend nearly doubles. Improving efficiency at increasing scale is not how
paid acquisition behaves; it is the signature of a product whose growth is
not primarily bought.

### Chosen specification

Model in growth rates. Differencing detrends both series and breaks the
confound.

```
Δlog(revenue)_t = β0 + β1·Δlog(spend)_t + β2·Δlog(spend)_{t-1} + ε_t
```

| Parameter | Fitted | p-value | Meaning |
|---|---|---|---|
| β0 | 0.035 | — | baseline monthly growth, no extra marketing |
| β1 | 0.301 | 0.0007 | same-month response to spend change |
| β2 | 0.208 | 0.0127 | following-month carryover |

Adjusted R² 0.471, versus 0.252 without the carryover term. Bootstrap on
the single-term elasticity (5,000 reps): mean 0.19, 95% interval [0.09,
0.33], P(β<0) = 0.002. The effect is real, small, and bounded well away
from 5.07.

Converted to the same €-per-€ terms as the naive model's 5.07, at current
spend and revenue levels this specification implies roughly **€0.79** of
marginal revenue per €1 of marketing in the same month, or about **€2.12**
once the following month's carryover is included — the naive estimate
over-states marketing's return by roughly **6×** (short-run) to **2.4×**
(including carryover), not the order-of-magnitude a casual read of "5.07
vs. a small elasticity" might suggest.

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

The defensible specification is also the most accurate. It beats a random
walk by roughly 5×.

### Rejected

- **`revenue ~ spend`** — confounded, over-states marketing by an order of
  magnitude.
- **Geometric adstock with fitted decay λ** — grid search peaked at
  λ≈0.40 (long-run elasticity 0.42) but the surface was flat between 0.30
  and 0.55. Weakly identified. The unconstrained two-lag form avoids
  committing to a decay rate the data cannot pin down.
- **Saturation / Hill curves** — ROAS rises monotonically with no
  inflection across the whole sample. There is no diminishing-returns
  signal to fit. Fitting one would be inventing a parameter. Handled as a
  guardrail instead (a caution flag on budgets outside the tested range).
- **Seasonality** — 21 months cannot support 12 monthly terms, and there
  is no December spike in the data.
- **Any ML model** — 20 observations, one feature; and the VP must be able
  to explain the number to a CFO.
- **Meridian / Robyn / PyMC-Marketing** — the right tools at production
  scale. All assume multiple channels and ~2 years of weekly data. With 21
  monthly points and one undifferentiated spend column a Bayesian MMM
  would be prior-dominated, and it would mean shipping a multi-GB image to
  serve a two-parameter regression.

## Assumptions

1. Revenue is assumed net of platform fees. Currency assumed EUR.
2. Spend is a single undifferentiated marketing figure; no channel
   attribution.
3. Marketing effect is estimated from month-to-month variation, not from
   an incrementality experiment. This is correlation under a detrending
   assumption, not proven causation.
4. Baseline growth is assumed to continue at the fitted rate. It is
   user-adjustable because ~3.5%/month compounds to ~51%/year, which is a
   strong assumption over a 12-month horizon.
5. No seasonality is modelled — not estimable from 21 months, and no
   December spike is present in the data.
6. No saturation is modelled — the data shows no diminishing returns.
   Handled with an out-of-range warning instead.
7. Uplifts are user-supplied business judgment, applied outside the fitted
   model.
8. Uplifts are permanent or single-month; decay is not modelled.
9. Forecast horizon fixed at 12 months.
10. The dataset is synthetic and treated as such (see Deployment note,
    below).

### What I would do with more time

Geo holdout or spend-variation experiments to identify marketing effect
causally — the honest conclusion is that this data cannot cleanly separate
marketing from trend, and the fix is experimental design, not a fancier
regression. Then a proper MMM once channel-level weekly data exists.

## Deployment and production note

The dataset provided is synthetic, so the tool is deployed to Streamlit
Community Cloud for evaluation convenience — the VP opens a link, no
installation required. Three launch paths are available:

| Audience | Action | Requirement |
|---|---|---|
| VP of Product | Opens the hosted link | None |
| Interview panel | `docker build && docker run` | Docker |
| Anyone with Python | Double-click `run.bat` / `run.sh` | Python 3.12 |

The application is containerized (see `Dockerfile`). Streamlit Community
Cloud performs its own containerization from `requirements.txt`, so the
hosted app and the local container are built from the same pinned
dependency set.

(This table is quoted from the frozen spec as written. A fourth path was
added afterward for anyone with Docker but no terminal — see
[Docker, no terminal needed](#docker-no-terminal-needed) above.)

In production the same application would run on internal infrastructure: a
private container service inside the company VPC (ECS/Fargate, Cloud Run
with internal ingress, or an internal Kubernetes namespace), behind SSO,
with no public ingress. Revenue and marketing spend are commercially
sensitive and would not leave the corporate network. Free public hosting
is an evaluation convenience, not a deployment recommendation. The
application layer is unchanged — that is the point of containerizing it.
What changes is the registry, the ingress rules, and an auth proxy.

Historical data would be read from the warehouse rather than a bundled
CSV, the model refit on a monthly cadence as actuals land, and saved
scenarios persisted to a database rather than session state.

**Hosting notes:** the free tier requires a public GitHub repository and
provides roughly 1 GB of memory (ample for 21 rows and a two-parameter
regression). Apps sleep after 12 hours without traffic, so the first visit
after a quiet period takes about a minute to wake — a slow first load is
not a broken app.

## A note on effort

This build ran well beyond the brief's recommended 2–3 hours because the
exercise front-loads a genuinely confounded modelling problem — spend and
organic growth are nearly inseparable in the raw data — that needed real
specification work before any code existed. Verification throughout ran
against the real environment rather than being assumed: the real Docker
image, the real pinned dependencies, the real rendered charts, catching
problems that local shortcuts would have missed. Under a soft time cap,
this build chose verified over fast; the full account is in
`AI_INTERACTIONS.md`.
