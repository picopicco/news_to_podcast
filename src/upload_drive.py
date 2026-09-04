"""Upload a file to the configured Google Drive folder.

Usage:
  python upload_drive.py podcast_20260905.wav "Podcast 2026-09-05"
"""
import json
import mimetypes
import sys

import requests

from drive_common import DRIVE_UPLOAD_URL, folder_id, get_token


def upload(file_path, name):
    token = get_token()
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    metadata = {"name": name, "parents": [folder_id()]}

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    files = {
        "metadata": ("metadata", json.dumps(metadata), "application/json"),
        "file": (name, file_bytes, mime_type),
    }
    resp = requests.post(
        DRIVE_UPLOAD_URL,
        headers={"Authorization": f"Bearer {token}"},
        files=files,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Drive upload failed: {resp.status_code} {resp.text}")

    return resp.json()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: upload_drive.py <file_path> <drive_file_name>", file=sys.stderr)
        sys.exit(1)

    result = upload(sys.argv[1], sys.argv[2])
    print(json.dumps(result, ensure_ascii=False, indent=2))
