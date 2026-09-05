"""Usage/quota report across every service this pipeline touches. Meant
to be run manually (double-click the desktop launcher), not scheduled.

- Google Cloud TTS: character count self-logged locally by
  synthesize.py, compared against the combined Neural2/Studio/Chirp3-HD
  free tier (1,000,000 chars/month) with a cost estimate beyond that.
- Gemini API: token counts self-logged locally by summarize.py. Google
  moved the Gemini API to a prepaid-credit billing model, and there is
  no simple API to read the remaining balance, so this reports raw
  usage only -- check https://aistudio.google.com/projects for the
  actual remaining credit/spend.
- Google Drive storage: read directly from the Drive API (authoritative,
  reflects the user's actual plan, including any paid Google One
  storage).
- Instapaper: free / no metered quota, not tracked.

Usage:
  python check_usage.py
"""
import calendar
import datetime
import os
import sys
from pathlib import Path

import drive_common
import usage_log

ROOT = Path(__file__).resolve().parent.parent

TTS_FREE_CHARS_PER_MONTH = 1_000_000
TTS_PRICE_PER_MILLION_CHARS = 16.0  # Neural2 (this pipeline's default tier)
WARN_THRESHOLD = 0.8  # warn at 80% of free tier


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def format_bytes(n):
    if n is None:
        return "unknown"
    n = int(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def report_line(label, used, limit):
    pct = (used / limit * 100) if limit else 0
    flag = "*WARN* " if pct >= WARN_THRESHOLD * 100 else ""
    return f"{flag}{label}: {used:,} / {limit:,} ({pct:.1f}%)"


def main():
    load_env(ROOT / ".env")
    today = datetime.date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]

    print(f"=== 利用状況レポート ({today.isoformat()}) ===\n")

    # --- Google Cloud TTS (self-logged) ---
    tts_chars = usage_log.month_total("tts_chars", "chars", today)
    print("[Google Cloud Text-to-Speech] (Neural2/Studio/Chirp3-HD 共通無料枠)")
    print(" " + report_line(f"{today.year}-{today.month:02d} 累計文字数", tts_chars, TTS_FREE_CHARS_PER_MONTH))
    projected_chars = tts_chars / today.day * days_in_month if today.day else 0
    print(f"  月末までの予測: 約{projected_chars:,.0f}文字")
    if tts_chars > TTS_FREE_CHARS_PER_MONTH:
        over = tts_chars - TTS_FREE_CHARS_PER_MONTH
        est_cost = over / 1_000_000 * TTS_PRICE_PER_MILLION_CHARS
        print(f"  無料枠超過分の概算費用: ${est_cost:.2f} (Neural2想定)")
    print()

    # --- Gemini API (self-logged; no balance-read API under prepay billing) ---
    gemini_tokens = usage_log.month_total("gemini_tokens", "total_tokens", today)
    print("[Gemini API] (前払いクレジット制、残高はAPIから取得できません)")
    print(f"  {today.year}-{today.month:02d} 累計トークン数: {gemini_tokens:,}")
    print("  実際の残高・請求額は https://aistudio.google.com/projects で確認してください")
    print()

    # --- Google Drive storage (authoritative) ---
    print("[Google Drive ストレージ] (ユーザー本人のアカウント)")
    try:
        token = drive_common.get_token()
        quota = drive_common.storage_quota(token)
        used = int(quota.get("usage", 0))
        limit = quota.get("limit")
        if limit:
            print(" " + report_line("使用量", used, int(limit)))
        else:
            print(f"  使用量: {format_bytes(used)} (上限なし/無制限アカウント)")
    except Exception as e:
        print(f"  取得できませんでした: {e}", file=sys.stderr)
        print("  取得できませんでした(認証情報を確認してください)")
    print()

    print("[Instapaper API] 無料・従量課金なし (監視対象外)")


if __name__ == "__main__":
    main()
