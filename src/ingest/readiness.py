"""Milestone 2: turn Garmin's noisy JSON into a compact daily readiness summary.

This is the clean object the reasoning layer consumes. Design goals:
- Only the fields that inform "how ready is my body to train today".
- Robust to missing data (a not-yet-synced day returns nulls, not crashes).
- Numbers + Garmin's own feedback phrases (e.g. HRV_BALANCED_8), which are
  human-meaningful and let the LLM interpret trends without a fragile int map.
"""
from datetime import date
from typing import Any


def _min(seconds: Any) -> float | None:
    return round(seconds / 60, 1) if isinstance(seconds, (int, float)) else None


def _hours(seconds: Any) -> float | None:
    return round(seconds / 3600, 2) if isinstance(seconds, (int, float)) else None


def _first_value(mapping: Any) -> dict:
    """Garmin nests some data under a device-id key; grab the first device."""
    if isinstance(mapping, dict) and mapping:
        return next(iter(mapping.values()))
    return {}


def summarize_sleep(sleep: dict) -> dict:
    dto = (sleep or {}).get("dailySleepDTO") or {}
    scores = dto.get("sleepScores") or {}
    overall = scores.get("overall") or {}
    need = dto.get("sleepNeed") or {}
    return {
        "hours": _hours(dto.get("sleepTimeSeconds")),
        "score": overall.get("value"),
        "score_qualifier": overall.get("qualifierKey"),
        "feedback": dto.get("sleepScoreFeedback"),
        "deep_min": _min(dto.get("deepSleepSeconds")),
        "light_min": _min(dto.get("lightSleepSeconds")),
        "rem_min": _min(dto.get("remSleepSeconds")),
        "awake_min": _min(dto.get("awakeSleepSeconds")),
        "avg_sleep_hr": dto.get("avgHeartRate"),
        "avg_sleep_stress": dto.get("avgSleepStress"),
        "need_baseline_min": need.get("baseline"),
        "need_actual_min": need.get("actual"),
        "need_feedback": need.get("feedback"),
    }


def summarize_hrv(hrv: dict) -> dict:
    summary = (hrv or {}).get("hrvSummary") or {}
    baseline = summary.get("baseline") or {}
    return {
        "last_night_avg": summary.get("lastNightAvg"),
        "weekly_avg": summary.get("weeklyAvg"),
        "status": summary.get("status"),
        "baseline_low": baseline.get("balancedLow"),
        "baseline_high": baseline.get("balancedUpper"),
        "feedback": summary.get("feedbackPhrase"),
    }


def summarize_training(ts: dict) -> dict:
    status = _first_value(
        (ts or {}).get("mostRecentTrainingStatus", {}).get("latestTrainingStatusData")
    )
    balance = _first_value(
        (ts or {}).get("mostRecentTrainingLoadBalance", {}).get(
            "metricsTrainingLoadBalanceDTOMap"
        )
    )
    vo2 = ((ts or {}).get("mostRecentVO2Max") or {}).get("generic")
    return {
        "status_code": status.get("trainingStatus"),
        "since_date": status.get("sinceDate"),
        "load_balance_feedback": balance.get("trainingBalanceFeedbackPhrase"),
        "monthly_load": {
            "aerobic_low": round(balance["monthlyLoadAerobicLow"])
            if balance.get("monthlyLoadAerobicLow") is not None
            else None,
            "aerobic_high": round(balance["monthlyLoadAerobicHigh"])
            if balance.get("monthlyLoadAerobicHigh") is not None
            else None,
            "anaerobic": round(balance["monthlyLoadAnaerobic"])
            if balance.get("monthlyLoadAnaerobic") is not None
            else None,
        },
        "vo2max": (vo2 or {}).get("vo2MaxValue") if isinstance(vo2, dict) else vo2,
    }


def summarize_activities(activities: list, limit: int = 7) -> list:
    out = []
    for a in (activities or [])[:limit]:
        out.append(
            {
                "name": a.get("activityName"),
                "type": (a.get("activityType") or {}).get("typeKey"),
                "start": a.get("startTimeLocal"),
                "dur_min": _min(a.get("duration")),
                "load": round(a["activityTrainingLoad"])
                if a.get("activityTrainingLoad") is not None
                else None,
            }
        )
    return out


def build_summary(client, target_date: str | None = None) -> dict:
    """Pull one day + recent activities and return a compact readiness summary."""
    d = target_date or date.today().isoformat()

    stats = client.get_stats(d) or {}
    sleep = client.get_sleep_data(d) or {}
    hrv = client.get_hrv_data(d) or {}
    training = client.get_training_status(d) or {}
    activities = client.get_activities(0, 7) or []

    return {
        "date": d,
        "sleep": summarize_sleep(sleep),
        "hrv": summarize_hrv(hrv),
        "resting_hr": {
            "today": stats.get("restingHeartRate"),
            "seven_day_avg": stats.get("lastSevenDaysAvgRestingHeartRate"),
        },
        "body_battery": {
            "most_recent": stats.get("bodyBatteryMostRecentValue"),
            "high": stats.get("bodyBatteryHighestValue"),
            "low": stats.get("bodyBatteryLowestValue"),
            "at_wake": stats.get("bodyBatteryAtWakeTime"),
        },
        "stress": {
            "avg": stats.get("averageStressLevel"),
            "qualifier": stats.get("stressQualifier"),
        },
        "respiration": {"avg_waking": stats.get("avgWakingRespirationValue")},
        "intensity_minutes": {
            "moderate": stats.get("moderateIntensityMinutes"),
            "vigorous": stats.get("vigorousIntensityMinutes"),
            "goal": stats.get("intensityMinutesGoal"),
        },
        "steps": {"total": stats.get("totalSteps"), "goal": stats.get("dailyStepGoal")},
        "training": summarize_training(training),
        "recent_activities": summarize_activities(activities),
    }
