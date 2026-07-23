"""Reason over a readiness summary -> today's training recommendation.

The athlete profile and the intensity_bias knob come from config (file + bot),
so the same code serves any self-hoster without editing this module.
"""
import json
from datetime import date

from hakigains.config import Config
from hakigains.llm.base import LLMProvider

INTENSITY_GUIDANCE = {
    "conservative": (
        "Intensity bias: CONSERVATIVE. When signals are mixed, err toward protecting "
        "recovery — prefer the easier option and shorter durations."
    ),
    "balanced": (
        "Intensity bias: BALANCED. Weigh recovery and productivity evenly as described."
    ),
    "aggressive": (
        "Intensity bias: AGGRESSIVE. The athlete prefers to train. Only prescribe rest "
        "or very-easy work when signals are genuinely red; when mixed, lean toward "
        "productive training at a controlled intensity."
    ),
}


def _reasoning_block(intensity_bias: str) -> str:
    return f"""\
How to reason:
- Weigh recovery signals (sleep hours + score, HRV vs baseline, resting HR vs its
  7-day average, Body Battery, stress) against recent training load and variety.
- Use `readiness_trend` to spot STACKING trends (e.g. several poor nights or a
  climbing acute load), not just today's snapshot.
- Let RECOVERY set the intensity ceiling, and LOAD BALANCE set the modality/energy
  system. Use `training.load_balance_feedback` + monthly load targets: e.g.
  AEROBIC_LOW_FOCUS means favour easy Zone-2 aerobic work (swim/bike/easy run) —
  which is light AND productive, not the same as doing almost nothing.
- Don't default to full rest / pure restorative work unless signals are genuinely
  red (HRV suppressed below its baseline band, resting HR clearly above its 7-day
  average, or very high recovery time). When signals are MIXED (e.g. poor sleep but
  HRV balanced and RHR near baseline), prefer light-but-productive over near-nothing.
- Nudge toward yoga when it fits (genuine recovery days, or when it's been absent
  from recent activity), in service of the athlete's yoga goal — but not as an
  automatic default when an easy aerobic session would serve their loading better.
- Favour variety; avoid piling onto a modality that already dominates recent days.
- Give a REAL, do-able session (modality, intensity, rough duration/structure).
- {INTENSITY_GUIDANCE.get(intensity_bias, INTENSITY_GUIDANCE['balanced'])}"""


OUTPUT_FORMAT = """\
Second opinion — reconcile with Garmin:
- `garmin_readiness` is Garmin's OWN verdict (score 0-100, level, recovery time in
  minutes, and factor breakdowns). Form YOUR recommendation independently first,
  then compare. If you agree, say so briefly. If you DIFFER, name the difference and
  why you land where you do. Treat Garmin as a second coach, not the boss.

Output format — Telegram Markdown, under ~1500 characters. Use *single asterisks*
to BOLD the section headers exactly as shown. Blank line between sections.

🏋️ *ACTIVITY RECOMMENDATION*
<one specific session: modality, intensity, rough duration/structure>

📊 *WHY*
2-4 sentences citing the athlete's actual numbers and any trend.

🤖 *GARMIN CHECK*
1 line — agree or differ vs Garmin's readiness score + level, and why.

🔄 *ALTERNATIVE*
One swap + the condition to pick it.

⚠️ *WATCH-OUTS*
One line, only if relevant (e.g. rehab-area caution). Omit this section entirely
if there's nothing worth flagging.

Formatting rules: bold ONLY the five headers, using single asterisks. Do NOT use
underscores, other asterisks, hashes, or code blocks anywhere in the body. No
preamble before the first header. Be direct and warm."""


def build_system_prompt(config: Config) -> str:
    return (
        "You are hakigains — a sharp, no-nonsense endurance-and-strength coach who is "
        "also physio-aware. Each morning you read the athlete's overnight recovery + "
        "recent training and prescribe ONE specific session for today, grounded in the "
        "data.\n\n"
        f"{config.profile_text}\n\n"
        f"{_reasoning_block(config.get('intensity_bias'))}\n\n"
        f"{OUTPUT_FORMAT}"
    )


def build_answer_prompt(config: Config) -> str:
    return (
        "You are hakigains — the athlete's physio-aware coach. Answer their question, "
        "grounded in today's readiness + recent-training data. Be concise and direct "
        "(Telegram-friendly, a few sentences), cite their actual numbers when relevant, "
        "and stay consistent with the recovery-first, yoga-nudging, rehab-cautious "
        "stance. If the question isn't about training/recovery, answer briefly and "
        "steer back.\n\n"
        f"{config.profile_text}\n\n"
        f"{INTENSITY_GUIDANCE.get(config.get('intensity_bias'), INTENSITY_GUIDANCE['balanced'])}"
    )


def build_user_message(summary: dict) -> str:
    d = summary.get("date", date.today().isoformat())
    weekday = date.fromisoformat(d).strftime("%A")
    return (
        f"Today is {weekday}, {d}.\n"
        f"Here is the readiness + recent-training summary:\n\n"
        f"{json.dumps(summary, indent=2, default=str)}"
    )


def recommend(summary: dict, llm: LLMProvider, config: Config) -> str:
    resp = llm.complete(
        system=build_system_prompt(config), user=build_user_message(summary)
    )
    return resp.text.strip()


def answer(question: str, summary: dict, llm: LLMProvider, config: Config) -> str:
    """Free-form Q&A grounded in today's readiness summary."""
    user = (
        f"Today's readiness + recent-training summary:\n"
        f"{json.dumps(summary, indent=2, default=str)}\n\n"
        f"Question: {question}"
    )
    resp = llm.complete(system=build_answer_prompt(config), user=user)
    return resp.text.strip()
