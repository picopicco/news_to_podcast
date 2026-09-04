"""Shared Google Drive helpers used by the other scripts.

Uploads happen as the user's own Google account via OAuth (refresh
token), so files are owned by the user and count against their own
Drive storage plan -- not a service account's.

Required env vars:
  GOOGLE_OAUTH_CLIENT_ID
  GOOGLE_OAUTH_CLIENT_SECRET
  GOOGLE_OAUTH_REFRESH_TOKEN
  GOOGLE_DRIVE_FOLDER_ID        target folder ID (owned by the user)
"""
import json
import os

import requests

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def get_token():
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
            "refresh_token": os.environ["GOOGLE_OAUTH_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def folder_id():
    return os.environ["GOOGLE_DRIVE_FOLDER_ID"]


def find_file(token, name, parent_id=None):
    """Return the first non-trashed Drive file matching `name` (and parent, if given), or None."""
    parent_id = parent_id or folder_id()
    query = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
    resp = requests.get(
        DRIVE_FILES_URL,
        headers={"Authorization": f"Bearer {token}"},
        params={"q": query, "fields": "files(id, name, modifiedTime, mimeType)"},
    )
    resp.raise_for_status()
    files = resp.json().get("files", [])
    return files[0] if files else None


def list_files(token, parent_id=None, extra_query=None, fields="files(id, name, modifiedTime, mimeType, size)"):
    parent_id = parent_id or folder_id()
    query = f"'{parent_id}' in parents and trashed = false"
    if extra_query:
        query += f" and {extra_query}"
    files = []
    page_token = None
    while True:
        params = {"q": query, "fields": f"nextPageToken, {fields}", "pageSize": 1000}
        if page_token:
            params["pageToken"] = page_token
        resp = requests.get(
            DRIVE_FILES_URL, headers={"Authorization": f"Bearer {token}"}, params=params
        )
        resp.raise_for_status()
        data = resp.json()
        files.extend(data.get("files", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return files


def download_file_content(token, file_id):
    resp = requests.get(
        f"{DRIVE_FILES_URL}/{file_id}",
        headers={"Authorization": f"Bearer {token}"},
        params={"alt": "media"},
    )
    resp.raise_for_status()
    return resp.content


def download_json(token, name, parent_id=None, default=None):
    existing = find_file(token, name, parent_id)
    if not existing:
        return default
    content = download_file_content(token, existing["id"])
    return json.loads(content.decode("utf-8"))


def upload_json(token, name, data, parent_id=None):
    parent_id = parent_id or folder_id()
    existing = find_file(token, name, parent_id)
    payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    if existing:
        update_url = f"https://www.googleapis.com/upload/drive/v3/files/{existing['id']}?uploadType=multipart"
        resp = requests.patch(
            update_url,
            headers={"Authorization": f"Bearer {token}"},
            files={
                "metadata": ("metadata", json.dumps({"name": name}), "application/json"),
                "file": (name, payload, "application/json"),
            },
        )
    else:
        metadata = {"name": name, "parents": [parent_id]}
        resp = requests.post(
            DRIVE_UPLOAD_URL,
            headers={"Authorization": f"Bearer {token}"},
            files={
                "metadata": ("metadata", json.dumps(metadata), "application/json"),
                "file": (name, payload, "application/json"),
            },
        )
    resp.raise_for_status()
    return resp.json()


def delete_file(token, file_id):
    resp = requests.delete(
        f"{DRIVE_FILES_URL}/{file_id}", headers={"Authorization": f"Bearer {token}"}
    )
    resp.raise_for_status()


def storage_quota(token):
    resp = requests.get(
        "https://www.googleapis.com/drive/v3/about",
        headers={"Authorization": f"Bearer {token}"},
        params={"fields": "storageQuota"},
    )
    resp.raise_for_status()
    return resp.json().get("storageQuota", {})
