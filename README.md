# hakigains 🏴‍☠️

A self-hosted, **injury-aware AI training coach** over your Garmin data. Each morning it reads
your overnight recovery (sleep, HRV, resting HR, Body Battery, training load) plus Garmin's own
readiness verdict, reasons over the trend against **your** goals, and pushes **one specific
session** to your phone via Telegram — with a second-opinion cross-check against Garmin. You can
also chat with it.

Your coaching bias isn't baked into the code — it comes from a profile *you* own (`config.yaml`).
It is a **scheduled workflow with an LLM reasoning step** plus a gated interactive bot, not an
autonomous agent. See [docs/PRODUCT.md](docs/PRODUCT.md) for the full design and the explicit
**built vs not-yet** feature list (e.g. calendar integration is *not* built yet).

## Self-hosting

Your Garmin credentials **stay on your own machine** — there is no central service. You run
your own copy with your own bot. (Why it must be self-hosted, not a shared bot:
[docs/PRODUCT.md](docs/PRODUCT.md).)

### 1. Install
```bash
python -m venv .venv && . .venv/Scripts/activate    # (or .venv/bin/activate on *nix)
pip install -e .
```

### 2. Configure
```bash
cp .env.example .env                  # fill in Garmin, LLM, and Telegram values
cp config.example.yaml config.yaml    # your profile + default knobs
```
- **Telegram bot:** create one via @BotFather (`/newbot`), put the token in `.env`, then
  message your new bot once and run `python scripts/telegram_setup.py` to capture your chat ID.
- **LLM:** set `LLM_PROVIDER` + provider keys in `.env` (Azure OpenAI supported today).

### 3. Run
```bash
python scripts/smoke_llm.py                 # verify the LLM is reachable
python scripts/run_briefing.py --dry        # generate today's briefing (print only)
python scripts/run_briefing.py              # generate + send to Telegram
python scripts/run_listener.py              # interactive bot (always-on process)
```

### Talking to the bot
- `/brief` — today's recommended session
- `/settings` — show your current knobs
- `/set <knob> <value>` — e.g. `/set intensity_bias aggressive` (knobs: `activity_window`,
  `trend_days`, `intensity_bias`)
- …or just ask it anything about your training/recovery.

The bot is **gated to your own chat ID** — it ignores everyone else.

## Deploying to AWS (optional)
Run it serverless (daily briefing on a schedule + webhook bot) instead of always-on locally.
See [docs/DEPLOY.md](docs/DEPLOY.md).

## Layout
```
src/hakigains/   the package (config, garmin_client, llm, ingest, reason, deliver, bot)
scripts/         local entry points (run_briefing, run_listener, smoke_llm, ...)
deploy/          Lambda handler, Dockerfile, SAM template
docs/            PRODUCT.md (design), DEPLOY.md (runbook)
```
