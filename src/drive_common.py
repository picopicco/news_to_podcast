"""Shared Google Drive helpers used by the other scripts.

Uploads happen as the user's own Google account via OAuth (refresh
token), so files are owned by the user and count against their own
Drive storage plan -- not a service account's (which has zero storage
quota and cannot own files at all).

Required env vars:
  GOOGLE_OAUTH_CLIENT_ID
  GOOGLE_OAUTH_CLIENT_SECRET
  GOOGLE_OAUTH_REFRESH_TOKEN
  GOOGLE_DRIVE_FOLDER_ID        target folder ID (owned by the user)
"""
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
