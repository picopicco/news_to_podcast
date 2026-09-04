"""Standalone usage/quota report -- run this manually (not part of the
daily pipeline) to see how close each free tier is to being exceeded.

- Google Cloud TTS: character count is self-logged by synthesize.py into
  _usage_log.json on Drive (no Cloud Monitoring access needed). Compared
  against the combined Neural2/Studio/Chirp3-HD free tier: 1,000,000
  characters/month.
- Google Drive storage: read directly from the Drive API (authoritative,
  reflects the user's actual plan limit, including any paid Google One
  storage).
- Instapaper: free / no metered quota, not tracked.

Usage:
  python check_usage.py
"""
import calendar
import datetime
import sys

import drive_common

TTS_FREE_CHARS_PER_MONTH = 1_000_000
WARN_THRESHOLD = 0.8  # warn at 80% of free tier


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
    flag = "⚠ " if pct >= WARN_THRESHOLD * 100 else ""
    return f"{flag}{label}: {used:,} / {limit:,} ({pct:.1f}%)"


def main():
    token = drive_common.get_token()

    # --- TTS usage (self-logged) ---
    log = drive_common.download_json(token, "_usage_log.json", default={"tts_chars": []})
    today = datetime.date.today()
    month_start = today.replace(day=1)
    this_month_chars = sum(
        entry["chars"]
        for entry in log.get("tts_chars", [])
        if datetime.date.fromisoformat(entry["date"]) >= month_start
    )
    days_in_month = calendar.monthrange(today.year, today.month)[1]

    print(f"=== 使用状況レポート ({today.isoformat()}) ===\n")
    print("[Google Cloud Text-to-Speech] (Neural2/Studio/Chirp3-HD 共通無料枠)")
    print(
        " "
        + report_line(
            f"{today.year}-{today.month:02d} 累計文字数",
            this_month_chars,
            TTS_FREE_CHARS_PER_MONTH,
        )
    )
    projected = this_month_chars / today.day * days_in_month if today.day else 0
    print(f"  月末までの予測: 約{projected:,.0f}文字")
    print()

    # --- Drive storage (authoritative; may be unavailable with the
    # narrow drive.file scope, which doesn't always expose account-wide
    # quota) ---
    print("[Google Drive ストレージ] (ユーザー本人のアカウント)")
    try:
        quota = drive_common.storage_quota(token)
        used = int(quota.get("usage", 0))
        limit = quota.get("limit")
        if limit:
            print(" " + report_line("使用量", used, int(limit)))
        else:
            print(f"  使用量: {format_bytes(used)} (上限なし/無制限アカウント)")
    except Exception as e:
        print(f"  取得できませんでした(スコープ不足の可能性): {e}", file=sys.stderr)
        print("  取得できません(drive.fileスコープでは権限不足の場合があります)")
    print()

    print("[Instapaper API] 無料・従量課金なし (監視対象外)")


if __name__ == "__main__":
    main()
