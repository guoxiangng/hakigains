# hakigains — Product Notes

> **Haki** (One Piece) — *Kenbunshoku*, the observation sense that reads what's coming.
> hakigains observes your body's signals and recommends how to train today. Plus a pun on *gains*.

A **self-hosted AI training coach** over your Garmin data. Each morning it reads your overnight
recovery, reasons over the trend against *your* goals and constraints, cross-checks Garmin's own
readiness verdict, and pushes **one specific session** to your phone via Telegram. You can also
chat with it.

---

## 1. Vision

> Every morning, tell me what to train today — grounded in how my body actually is, my recent
> training, and my own goals — and let me push back or ask questions.

Not a rules engine, and not a fixed weekly plan: an **observation + reasoning** layer over your
own data that gives a *specific session with a rationale*, tuned by a profile **you** own.

## 2. Who configures what

hakigains ships with **no built-in athlete bias**. Everything personal lives in a per-user
`config.yaml` (copied from `config.example.yaml`, gitignored):

- **Profile** — free-form sections (training focus, preferred activities, injuries/constraints,
  notes). Rendered verbatim into the coach's prompt. This is where *your* specifics go (a rehab
  program, a yoga goal, a race, whatever) — not in the product code.
- **Runtime knobs** — `activity_window`, `trend_days`, `intensity_bias`
  (conservative / balanced / aggressive). Defaults live in the yaml; change them live via the
  bot's `/set`, persisted to `data/settings.json`.

## 3. Requirements → Jobs To Be Done

| # | As an athlete, I want… | So that… |
|---|------------------------|----------|
| R1 | a specific training recommendation each morning | I stop spending decision energy on "what today" |
| R2 | it grounded in my Garmin readiness (sleep, HRV, resting HR, Body Battery, load) | the call reflects how my body actually is |
| R3 | it to reason over a multi-day trend, not one snapshot | it catches stacking fatigue, not just today |
| R4 | it to respect my own goals + injuries (my profile) | advice fits *me* without editing code |
| R5 | a second opinion vs Garmin's own readiness | I can see when the two coaches agree or differ |
| R6 | to push back / ask questions from my phone | it fits a real morning with zero friction |
| R7 | my Garmin credentials to stay under my control | I'm not trusting a stranger's server with my account |

## 4. Feature set

### Built now ✅
- **Readiness ingest** — Garmin → a compact daily summary: sleep (score/stages/need), HRV
  (vs baseline), resting HR (vs 7-day avg), Body Battery, stress, respiration, intensity minutes,
  training status/load balance, and recent activities.
- **Modality normalization** — folds Garmin's indoor/outdoor type keys
  (`treadmill_running`+`running` → `run`, `cycling`+`indoor_cycling` → `bike`, …) into coarse
  buckets + a rolled-up `modality_counts`, so the coach reasons over clean variety.
- **Reasoning + recommendation** — one LLM call → a specific session with rationale, in a
  structured Telegram format (Activity / Why / Garmin check / Alternative / Watch-outs).
- **Garmin second opinion** — ingests Garmin's own training-readiness (score, level, recovery
  time, ACWR, factor breakdown); the coach forms its own call, then reconciles with Garmin's.
- **7-day readiness trend** — so the coach sees stacking patterns, not a single day.
- **Config-driven profile + knobs** — profile from file; `intensity_bias`, `activity_window`,
  `trend_days` from file defaults, changeable via bot `/set`.
- **Goal-tied repertoire expansion** — may suggest a modality outside the athlete's usual pattern,
  but only on a high relevance bar tied to a stated goal, flagged as "worth trying," occasional.
- **Interactive bot (gated)** — `/brief`, `/ping`, `/settings`, `/set`, and free-form coaching
  Q&A grounded in today's data. Locked to the owner's chat ID.
- **Delivery** — Telegram push (scheduled briefing) + interactive replies.
- **Deployment** — runs locally, or serverless on AWS (Lambda + EventBridge + Function URL +
  Secrets Manager + S3) via AWS SAM.

### Not yet — roadmap ⬜
These are **explicitly not in the current build**:
- **Calendar integration** — feeding appointments/events (e.g. a rehab schedule) as hard
  constraints. *Not implemented.* Today, constraints only influence the coach via free-text notes
  in the profile, which it treats as soft guidance — it does **not** read any calendar.
- **Feedback loop** — logging planned vs actual + how it felt, fed back as history. *Not built.*
- **Workout-library mapping** — mapping a recommendation to a real saved Garmin workout (and
  optionally scheduling it to the watch). *Not built* (the Garmin endpoints exist; the feature
  doesn't).
- **Evaluation** — tracking bot-rec vs Garmin-rec vs outcome over time. *Not built.*
- **Weather / facility awareness, second sport-specific models.** *Not built.*
- **Bedrock/Claude provider** — the LLM abstraction exists; only Azure OpenAI is implemented today.

## 5. Is it an "agent"?

| Level | What it is | This product? |
|-------|-----------|---------------|
| 0 | Cron + rules engine, no LLM | ✗ — deliberately not rules-based |
| 1 | **Scheduled workflow with an LLM reasoning step** | ✓ **the morning briefing** |
| 2 | **LLM with light tools / conversation** | ✓ **the interactive bot** (Q&A + commands) |
| 3 | **Autonomous agent taking real-world actions** | ✗ **never** — out of scope by design |

hakigains is a **Level-1 workflow** plus a **Level-2 interactive layer**. It is not autonomous:
it recommends and answers; it does not act on your accounts or calendar. This keeps it cheap,
reliable, and easy to reason about.

## 6. Interaction model — Telegram

Two modes: **push** (the scheduled briefing arrives unprompted) and **pull** (you reply, ask
"why", or tweak a knob). Telegram covers both on mobile with near-zero friction.

**Security (hard rules):** bots are publicly reachable — anyone can *message* the bot, so safety
comes from what it *does*. The very first step on any inbound message is a **chat-ID allowlist**;
unknown senders are ignored and never touch data, the LLM, or Garmin. Outbound is pinned to the
owner's chat ID. The bot **token** is a real secret (rotate via BotFather `/revoke` on exposure).
Telegram bot chats are not end-to-end encrypted — fine for training tips, not for anything you'd
treat as medical-record sensitive.

## 7. Architecture

```
                     ┌──────────────────────────────────────────┐
   EventBridge  ───► │  SCHEDULED (daily briefing)               │
   (cron)            │  ingest ─► reason ─► deliver (Telegram)   │
                     └──────────────────────────────────────────┘
   Telegram    ───►  ┌──────────────────────────────────────────┐
   webhook /         │  INTERACTIVE (on demand)                  │
   long-poll         │  bot/core (GATED) ─► /brief · /set · Q&A  │
                     └──────────────────────────────────────────┘

   Config:  profile (config.yaml, file) + knobs (data/settings.json, via /set)
   Secrets: Garmin creds, LLM key, Telegram token — never in the repo
   LLM:     provider abstraction — Azure OpenAI now, Bedrock/Claude later
```

**Package (`src/hakigains/`):** `config` · `garmin_client` · `ingest` · `reason` · `deliver` ·
`bot`. The chat-ID gate + routing live in `bot/core.py`, imported by **both** the local
long-poll listener and the Lambda webhook — so neither can skip the gate.

## 8. Runtime & hosting

**Runtime:** Python 3.12; `garminconnect`, `openai`, `requests`, `PyYAML`. Tiny compute footprint.

- **Local** — `pip install -e .`, run `scripts/run_briefing.py` (cron/Task Scheduler) and
  `scripts/run_listener.py` (always-on long-poll bot). Data never leaves your machine (except the
  LLM call).
- **AWS (SAM)** — container-image Lambdas: a scheduled briefing (EventBridge) and a Telegram
  **webhook** (Function URL). Secrets Manager holds creds; an S3 bucket persists the Garmin auth
  token + settings across cold starts (Lambda's filesystem is ephemeral, and Garmin rate-limits
  logins). See [DEPLOY.md](DEPLOY.md).

## 9. Security posture

- **Self-hosted trust model** — each user runs their own copy; Garmin credentials stay in *their*
  `.env` / *their* AWS account. There is no central service holding anyone's password. (A hosted
  multi-user version would need Garmin's official OAuth, whose developer program is currently on
  hold — so self-host is the path.)
- **Garmin: read-only** in practice (login is the only write).
- **One external egress to name honestly:** the reasoning step sends a *summarized* readiness
  picture to the LLM provider. On Azure OpenAI that data leaves your control; moving the provider
  to **Bedrock/Claude in your own AWS account** would close that egress. Send a clean summary, not
  raw exhaustive data.

## 10. Roadmap

1. ✅ Garmin ingest + readiness summary
2. ✅ Reasoning + briefing → Telegram
3. ✅ Garmin second opinion + 7-day trend
4. ✅ Interactive gated bot + config profile/knobs
5. ✅ Modality normalization + goal-tied repertoire expansion
6. ✅ AWS SAM deployment path
7. ⬜ Calendar constraints (hard scheduling/rehab constraints) — **not started**
8. ⬜ Feedback loop (planned vs actual vs felt) + evaluation
9. ⬜ Workout-library mapping (recommend/schedule a real saved workout)
10. ⬜ Bedrock/Claude provider; weather/facility awareness
