"""Local orchestrator for the daily news_to_podcast pipeline. Intended to
be run by Windows Task Scheduler once a day (see docs/task_scheduler.md).

Loads credentials from .env (next to this file), then runs each pipeline
step as a subprocess so failures in one step are isolated and logged.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def run(args, **kwargs):
    print(f"+ {' '.join(str(a) for a in args)}", flush=True)
    subprocess.run(args, check=True, **kwargs)


def main():
    load_env(ROOT / ".env")

    articles_path = ROOT / "articles.json"
    dialogue_path = ROOT / "dialogue.json"

    with open(articles_path, "w", encoding="utf-8") as out:
        run([sys.executable, str(SRC / "fetch_instapaper.py")], stdout=out)

    data = json.loads(articles_path.read_text(encoding="utf-8"))
    if data["article_count"] == 0:
        print("no unread articles saved in the last 24 hours, nothing to synthesize")
        articles_path.unlink(missing_ok=True)
        return

    run([sys.executable, str(SRC / "summarize.py"), str(articles_path), str(dialogue_path)])

    date_str = data["window_end_jst"][:10]
    out_wav = ROOT / f"podcast_{date_str.replace('-', '')}.wav"
    run([sys.executable, str(SRC / "synthesize.py"), str(dialogue_path), str(out_wav)])
    run([sys.executable, str(SRC / "upload_drive.py"), str(out_wav), f"Podcast {date_str}"])
    run([sys.executable, str(SRC / "cleanup_old_files.py")])

    print(f"done: {data['article_count']} article(s) covered, uploaded {out_wav.name}")

    for p in (articles_path, dialogue_path, out_wav):
        p.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
