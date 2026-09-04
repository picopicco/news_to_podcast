"""Delete podcast audio files older than RETENTION_DAYS from the Drive
folder. Scoped tightly on purpose so a photo/video someone drops in the
same folder is never touched:
  - only the configured GOOGLE_DRIVE_FOLDER_ID (not recursive)
  - only files whose name starts with "podcast_"
  - only files whose mimeType starts with "audio/"
  - only files older than RETENTION_DAYS

Usage:
  python cleanup_old_files.py
"""
import datetime
import sys

from drive_common import delete_file, get_token, list_files

RETENTION_DAYS = 15
NAME_PREFIX = "podcast_"


def parse_drive_time(s):
    # Drive returns RFC3339, e.g. "2026-08-20T05:00:00.000Z"
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
        tzinfo=datetime.timezone.utc
    )


def main():
    token = get_token()
    files = list_files(token)
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=RETENTION_DAYS
    )

    deleted = []
    for f in files:
        name = f.get("name", "")
        mime = f.get("mimeType", "")
        if not name.startswith(NAME_PREFIX):
            continue
        if not mime.startswith("audio/"):
            continue
        modified = parse_drive_time(f["modifiedTime"])
        if modified < cutoff:
            delete_file(token, f["id"])
            deleted.append(name)
            print(f"deleted: {name} (modified {modified.isoformat()})", file=sys.stderr)

    print(f"deleted {len(deleted)} file(s) older than {RETENTION_DAYS} days", file=sys.stderr)
    return deleted


if __name__ == "__main__":
    main()
