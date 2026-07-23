"""hakigains configuration.

Two layers, deliberately separated:
- **Profile** (facilities, goals, rehab context): rich, personal, stable — lives in
  `config.yaml` (copied from `config.example.yaml`), edited as a file. NOT settable
  via the bot.
- **Runtime knobs** (activity_window, trend_days, intensity_bias): simple scalars,
  changeable on the fly via the bot's /set command, persisted to data/settings.json,
  overriding the yaml defaults.

Paths are env-overridable (HAKIGAINS_CONFIG / HAKIGAINS_DATA_DIR) so the same code
runs from the repo locally and from a bundled image on Lambda.
"""
import json
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(os.environ.get("HAKIGAINS_CONFIG", ROOT / "config.yaml"))
CONFIG_EXAMPLE = ROOT / "config.example.yaml"
DATA_DIR = Path(os.environ.get("HAKIGAINS_DATA_DIR", ROOT / "data"))
SETTINGS_JSON = DATA_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "activity_window": 14,   # days of activity history to include
    "trend_days": 7,         # readiness-trend window
    "intensity_bias": "balanced",
}

# Validation for each knob the bot may set.
KNOB_SPEC = {
    "activity_window": {"type": int, "min": 1, "max": 60},
    "trend_days": {"type": int, "min": 1, "max": 30},
    "intensity_bias": {"type": str, "choices": {"conservative", "balanced", "aggressive"}},
}

@dataclass
class Config:
    profile: dict
    settings: dict

    @property
    def profile_text(self) -> str:
        return render_profile(self.profile)

    def get(self, key: str):
        return self.settings.get(key, DEFAULT_SETTINGS.get(key))


def _load_yaml() -> dict:
    path = CONFIG_PATH if CONFIG_PATH.exists() else CONFIG_EXAMPLE
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def render_profile(profile: dict) -> str:
    """Render the profile into the athlete-context block for the prompt.

    Sections are free-form: whatever headings the athlete writes under `profile:`
    are rendered verbatim, each followed by its list of lines. No fixed schema.
    """
    lines = ["Athlete profile:"]
    for section, items in profile.items():
        if not items:
            continue
        lines.append("")
        lines.append(f"{section}:")
        if isinstance(items, (list, tuple)):
            lines.extend(f"  - {item}" for item in items)
        else:
            lines.append(f"  {items}")
    return "\n".join(lines)


def load_settings() -> dict:
    settings = dict(DEFAULT_SETTINGS)
    yaml_settings = _load_yaml().get("settings") or {}
    settings.update({k: v for k, v in yaml_settings.items() if k in DEFAULT_SETTINGS})
    if SETTINGS_JSON.exists():
        try:
            settings.update(json.loads(SETTINGS_JSON.read_text(encoding="utf-8")))
        except Exception:
            pass
    return settings


def load_config() -> Config:
    data = _load_yaml()
    return Config(profile=data.get("profile", {}), settings=load_settings())


def set_setting(key: str, raw_value: str) -> str:
    """Validate + persist a runtime knob. Returns a human-readable result message."""
    if key not in KNOB_SPEC:
        return f"Unknown setting '{key}'. Options: {', '.join(KNOB_SPEC)}"

    spec = KNOB_SPEC[key]
    if spec["type"] is int:
        try:
            value: object = int(raw_value)
        except ValueError:
            return f"{key} must be a whole number."
        if not (spec["min"] <= value <= spec["max"]):
            return f"{key} must be between {spec['min']} and {spec['max']}."
    else:
        value = str(raw_value).lower()
        if value not in spec["choices"]:
            return f"{key} must be one of: {', '.join(sorted(spec['choices']))}."

    current = {}
    if SETTINGS_JSON.exists():
        try:
            current = json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
        except Exception:
            current = {}
    current[key] = value
    SETTINGS_JSON.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_JSON.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return f"Set {key} = {value}"
