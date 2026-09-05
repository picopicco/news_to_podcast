"""Local, per-day usage logging shared by summarize.py, synthesize.py,
and check_usage.py. Runs entirely on the local machine now (the pipeline
is no longer an ephemeral cloud sandbox), so a plain JSON file next to
the repo is enough -- no need to round-trip it through Drive.
"""
import datetime
import json
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "usage_log.json"


def _load():
    if not LOG_PATH.exists():
        return {}
    try:
        return json.loads(LOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data):
    LOG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append(category, **fields):
    """Append one entry to `category` (e.g. "tts_chars", "gemini_tokens")
    with today's date plus the given fields. Best-effort: swallows errors
    so a logging failure never breaks the actual pipeline step."""
    try:
        data = _load()
        entry = {"date": datetime.date.today().isoformat()}
        entry.update(fields)
        data.setdefault(category, []).append(entry)
        _save(data)
    except Exception as e:
        print(f"warning: failed to log usage ({category}): {e}")


def month_total(category, field, today=None):
    today = today or datetime.date.today()
    month_start = today.replace(day=1)
    data = _load()
    total = 0
    for entry in data.get(category, []):
        d = datetime.datetime.strptime(entry["date"], "%Y-%m-%d").date()
        if d >= month_start:
            total += entry.get(field, 0)
    return total
