# hakigains — Product Notes

> **Haki** (One Piece) — *Kenbunshoku*, the observation/perception sense that lets you read what's coming.
> This tool observes your body's signals and tells you how to train today. Plus a pun on *gains*.

---

## 1. Vision (one-liner)

> Every morning, tell me what to train today — reasoning over my body's readiness, my
> recovery constraints, my schedule, and my goals — and let me push back or log reality.

Not a rules engine. An **observation + reasoning** layer over my own data that gives me a
*specific session with a rationale*, not a generic "easy day / hard day" label.

---

## 2. User requirements → Jobs To Be Done

| # | As me, I want… | So that… |
|---|----------------|----------|
| R1 | a specific training recommendation each morning | I stop wasting decision energy on "what do I do today" |
| R2 | it to read my Garmin readiness (sleep, HRV, resting HR, Body Battery, training load) | the call is grounded in how my body actually is, not a fixed weekly plan |
| R3 | it to factor in my chiro / physio / TCM Tuina appointments | it never tells me to load a body part I'm rehabbing or that a session will aggravate |
| R4 | it to nudge me toward yoga | I actually progress on my stated goal instead of defaulting to running |
| R5 | it to use my huge library of saved Garmin workouts | the recommendation is a *real workout I can press start on*, not an abstract prescription |
| R6 | to push back and log what I actually did + how it felt | it learns my reality and the advice compounds over time |
| R7 | to interact with it from my phone | it fits into a morning with zero friction |
| R8 | my health data to stay under my control | I'm not handing sensitive data to some third-party SaaS |

---

## 3. Feature set

### A. Readiness sensing  *(the "Haki")*
- Pull from Garmin: sleep score/stages, HRV status, resting HR (+ 7-day trend), Body Battery,
  training status, training load balance (acute vs chronic), recovery time, VO2max trend.
- Detect trends, not just today's number: rising resting HR + suppressed HRV + accumulated
  load → flag **under-recovery**; well-recovered + low recent load → green light for intensity.

### B. Recommendation reasoning  *(the LLM step)*
- Reason over readiness + constraints + goals → output **one recommended session** with a
  short rationale.
- Example output: *"Zone-2 pool swim, 40 min. HRV is suppressed and physio flagged the left
  knee — this keeps your aerobic base without loading the joint."*
- **Map to a real saved workout** (R5): match the recommendation to one of my Garmin workouts
  where possible, so I can just press start.

### C. Constraint awareness  *(the interlink layer)*
- **Calendar**: today's / this week's chiro, physio, TCM Tuina → constrains intensity, body
  part, and timing.
- **Interlink rules** I maintain in my health project (e.g. "no heavy legs the day after
  physio") fed in as explicit constraints, not inferred.
- **Yoga goal** (R4): track frequency, nudge when I've drifted.
- **Facility / weather** (later): pool vs gym availability, studio class schedule, rain if an
  outdoor run is in play.

### D. Feedback & memory loop
- Log **planned vs actual** + a one-line subjective check-in (soreness / energy / motivation).
- History feeds back as trend context. **The app's own store is a local file** (JSON/SQLite),
  portable to S3/DynamoDB later — the standalone build does *not* couple to Obsidian.
  (Mirroring briefings into my personal Obsidian vault is a nice-to-have for *me*, kept
  separate from the app's data model.)
- **Weekly review**: adherence, load progression, yoga frequency vs goal.

### E. Interaction (Telegram)
- Morning briefing **pushed** to me.
- **Two-way**: "give me something shorter", "I'm travelling", "why that?" → it re-reasons.
- Quick logging of what I actually did.

### MVP cut
**In:** A + B (basic) + C (calendar only) + E (push briefing + simple logging).
**Later:** workout-library mapping, weather/facility, weekly review, Obsidian memory loop.

---

## 4. Interaction model — do I want a Telegram bot?

**Yes — Telegram is the right front end**, because the product needs *two* modes and Telegram
covers both on mobile with near-zero friction:

- **Push** (proactive): the morning briefing arrives without me asking.
- **Pull** (conversational): I reply to push back, ask "why", or log reality.

Alternatives and why they lose:
- **Email / Obsidian daily note** — push-only, no back-and-forth.
- **A CLI** — great for building, useless at 7am on my phone.
- **A custom app** — massive overkill for one user.

> **Security note:** lock the bot to *my own Telegram chat ID* — bots accept messages from
> anyone by default. Ignore all other senders.

---

## 5. Is it an "agent"?

Useful to be precise, because it drives the architecture and the risk profile.

| Level | What it is | Is it this product? |
|-------|-----------|---------------------|
| 0 | Cron + rules engine, no LLM | ✗ — I explicitly don't want rules-based |
| 1 | **Scheduled pipeline with an LLM reasoning step** — deterministic code gathers data, one LLM call reasons, output delivered | ✓ **the morning briefing** |
| 2 | **LLM with tools (agentic loop)** — the model decides which tools to call, iterates, holds conversation state | ✓ *thin layer* for interactive Q&A ("why?", "what about my knee?") |
| 3 | **Autonomous agent** — takes real-world actions on its own (books classes, edits calendar) | ✗ **never**, given my security posture |

**Verdict:** hakigains is mostly a **Level-1 workflow with an LLM in it**, plus an optional
**Level-2 thin agent** for the interactive side. It is *not* an autonomous agent, and
deliberately so. This matches the "prefer the simplest thing that works — a workflow over an
agent unless you truly need the flexibility" principle. The Level-1 core is cheaper, more
reliable, and far easier to debug than a full agent, and it's what does 90% of the value.

---

## 6. Architecture

```
                     ┌─────────────────────────────────────┐
                     │           SCHEDULED (daily)          │
   EventBridge /     │                                      │
   cron  ──────────► │  ingest.py   → clean daily summary   │
                     │     │  (Garmin: sleep/HRV/HR/load)    │
                     │     ▼                                 │
   Google Calendar ─►│  enrich.py   → + appointments,       │
   (constraints)     │     │           yoga cadence, rules  │
                     │     ▼                                 │
   History store  ──►│  reason.py   → LLM call → session +   │
   (past recs+logs)  │     │           rationale            │
                     │     ▼                                 │
                     │  deliver.py  → Telegram push          │
                     └─────────────────────────────────────┘

                     ┌─────────────────────────────────────┐
   Telegram msg ────►│         INTERACTIVE (on demand)      │
   (webhook/poll)    │  bot.py → thin agent: query history, │
                     │           re-reason, log actual      │
                     └─────────────────────────────────────┘

   Secrets: Garmin creds + token, Anthropic key, Telegram token  (never in repo)
   State:   history of {planned, actual, felt}  → local JSON/SQLite → S3 / DynamoDB later
   LLM:     provider abstraction — OpenAI now, Bedrock/Claude later
```

**Components (shared code, two entry points):**
- `ingest` — Garmin pull → clean, denoised daily summary (not raw time-series).
- `enrich` — merge calendar constraints, yoga cadence, my health-project interlink rules.
- `reason` — single LLM call behind a **provider abstraction** (`llm/` interface):
  readiness + constraints + goals → recommended session. Swap providers without touching
  callers — **OpenAI now** (temporary key), **Bedrock/Claude later** (the security-ideal:
  reasoning stays inside my own AWS account).
- `deliver` — format + push to Telegram.
- `bot` — interactive handler (the thin Level-2 piece).

---

## 7. Runtime & hosting

**Runtime:** Python 3.12 (garminconnect + garth are Python; Anthropic SDK is Python).
Compute footprint is *tiny* — a few runs a day + occasional messages. 128–256 MB is plenty.

**Dependencies of note:** `garminconnect` (+`garth`), an LLM SDK behind a thin provider
interface (`openai` now; `boto3` for Bedrock later), `requests`/`httpx`, Telegram
(`python-telegram-bot` for long-poll locally, or raw Bot API for webhook on Lambda).

### Hosting options

| Option | Fit | Pros | Cons |
|--------|-----|------|------|
| **Local always-on** (my machine / Pi / NAS) + cron | iteration | free, fast feedback, **data never leaves home**, long-poll needs no inbound port | uptime is on me |
| **AWS serverless** (EventBridge Scheduler → Lambda for briefing; Telegram **webhook** → Lambda Function URL; Secrets Manager; S3/DynamoDB for state) | production | scales to zero, ~free at this volume, secrets done right, **on-brand for my AWS content** | Garmin token must persist externally (S3/Secrets round-trip); container image easiest for packaging |
| **Small VPS / PaaS** (Fly.io, Railway, Oracle free tier, t4g.nano) | middle | persistent process = simplest long-poll bot | always-on cost + I patch the box |
| **GitHub Actions cron** | briefing only | free scheduler | no interactive bot; health data in CI is meh; coarse cron |

### Recommended path (phased)

- **Phase 1 — local.** Run it on my own machine: Task Scheduler/cron for the briefing +
  long-polling Telegram bot. Fastest iteration, data stays local, no infra to stand up. This
  is where we tune the reasoning prompt.
- **Phase 2 — AWS serverless** (once stable, and worth an article). EventBridge Scheduler →
  Lambda briefing; Telegram **webhook** → Lambda Function URL; Secrets Manager for Garmin
  creds + token + Anthropic key; S3 or DynamoDB (or Obsidian-via-git) for history.

> **Lambda gotcha to design for:** garth caches an auth token on the local filesystem, which
> is ephemeral on Lambda. Persist the token in S3/Secrets Manager, load it at cold start,
> refresh, and write it back — don't re-login every invocation (Garmin rate-limits logins).

---

## 8. Security posture

- **Garmin: read-only** in practice — we only read data (login is the only write).
- **No bank/brokerage access** — that was the *finance* idea; explicitly out of scope here.
- **Health data stays mine** — local, or my own AWS account. Not a third-party SaaS.
- **Token file** gitignored + tight perms; creds only in `.env` (local) / Secrets Manager (AWS).
- **Telegram** locked to my own chat ID.
- **One external egress to name honestly:** the reasoning step sends a *summarised* daily
  readiness picture to the LLM provider. With the **temporary OpenAI key**, that data leaves
  my control — so we send a clean summary, not raw exhaustive data. The **provider
  abstraction** exists partly for this: moving to **Bedrock/Claude** later keeps the reasoning
  call *inside my own AWS account*, closing this egress entirely. That's the security-ideal
  end state.

### Security — Telegram (hard rules)

Telegram bots are publicly discoverable and *anyone* can send them messages — you cannot
prevent strangers from messaging `@hakigains_coach_bot`. Safety comes from what the bot
*does* with those messages, not from hiding it. Non-negotiable rules:

1. **Chat-ID allowlist (the door).** The interactive bot's very first step on any inbound
   message is: `if chat_id != TELEGRAM_CHAT_ID: ignore`. It must **never** touch Garmin data,
   history, or the LLM for an unknown sender. Strangers can knock; the door only opens for me.
2. **Outbound is pinned.** `send_message` only ever sends to my configured chat ID — never
   echoes back to an arbitrary inbound chat.
3. **The token is the crown jewel.** Whoever holds `TELEGRAM_BOT_TOKEN` can impersonate the
   bot *and* read everything sent to it (`getUpdates`). Keep it in `.env`/Secrets Manager,
   never in the repo, and **rotate it** (BotFather → `/revoke`) after any exposure.
4. **Telegram is not end-to-end encrypted for bots.** Message contents pass through Telegram's
   servers. Acceptable for low-sensitivity training tips; do **not** send anything I'd treat
   as medical-record sensitive through it.

---

## 9. Roadmap

1. ✅ **Milestone 1** — Garmin auth + daily data pull (done).
2. **Milestone 2** — `ingest`: turn the raw pull into a clean daily readiness summary.
3. **Milestone 3** — `reason`: provider abstraction + first LLM call (OpenAI) → recommended
   session + rationale (local).
4. **Milestone 4** — Telegram push of the briefing.
5. **Milestone 5** — `enrich`: Google Calendar constraints + yoga cadence.
6. **Milestone 6** — feedback loop: log planned vs actual + subjective check-in.
7. **Milestone 7** — workout-library mapping (recommend a *real* saved workout).
8. **Milestone 8** — AWS serverless port (+ swap LLM provider to Bedrock/Claude, closing the
   external egress).
9. **Later** — Obsidian memory loop, weekly review, weather/facility.
