"""Fetch Instapaper bookmarks that are unread and were saved within the
last 24 hours, and dump their article text as JSON.

Required env vars:
  INSTAPAPER_CONSUMER_KEY
  INSTAPAPER_CONSUMER_SECRET
  INSTAPAPER_USERNAME
  INSTAPAPER_PASSWORD

Usage:
  python fetch_instapaper.py > articles.json
"""
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

import oauth2 as oauth
from bs4 import BeautifulSoup

ACCESS_TOKEN_URL = "https://www.instapaper.com/api/1/oauth/access_token"
BOOKMARKS_URL = "https://www.instapaper.com/api/1/bookmarks/list"
TEXT_URL = "https://www.instapaper.com/api/1/bookmarks/get_text"

# Japan has no DST, so a fixed UTC+9 offset is always correct and avoids
# depending on a tzdata package being present in the runtime.
JST = timezone(timedelta(hours=9))

UNREAD_PROGRESS_THRESHOLD = 1.0  # progress < this counts as unread
WINDOW_HOURS = 24


def window_bounds(now=None):
    now = now or datetime.now(JST)
    window_end = now
    window_start = now - timedelta(hours=WINDOW_HOURS)
    return window_start, window_end


def get_client():
    consumer_key = os.environ["INSTAPAPER_CONSUMER_KEY"]
    consumer_secret = os.environ["INSTAPAPER_CONSUMER_SECRET"]
    username = os.environ["INSTAPAPER_USERNAME"]
    password = os.environ["INSTAPAPER_PASSWORD"]

    consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)
    client = oauth.Client(consumer)
    body = urllib.parse.urlencode(
        {
            "x_auth_username": username,
            "x_auth_password": password,
            "x_auth_mode": "client_auth",
        }
    )
    resp, content = client.request(ACCESS_TOKEN_URL, method="POST", body=body)
    if resp.status != 200:
        raise RuntimeError(f"Instapaper xAuth failed: {resp.status} {content!r}")
    tokens = dict(x.split("=") for x in content.decode().split("&"))
    token = oauth.Token(key=tokens["oauth_token"], secret=tokens["oauth_token_secret"])
    return oauth.Client(consumer, token)


def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a"):
        if "href" in a.attrs:
            del a["href"]
    text = soup.get_text()
    text = re.sub(r"^.*https?://\S+.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_articles(now=None):
    window_start, window_end = window_bounds(now)
    ts_start = int(window_start.timestamp())
    ts_end = int(window_end.timestamp())

    client = get_client()
    # folder_id="unread" is Instapaper's default reading-list view (not
    # archived, not starred-only).
    params = urllib.parse.urlencode({"folder_id": "unread", "limit": 500})
    resp, content = client.request(f"{BOOKMARKS_URL}?{params}", method="POST")
    if resp.status != 200:
        raise RuntimeError(f"bookmarks/list failed: {resp.status} {content!r}")

    items = json.loads(content.decode())
    bookmarks = [b for b in items if b.get("type") == "bookmark"]

    targets = [
        b
        for b in bookmarks
        if ts_start <= b.get("time", 0) < ts_end
        and b.get("progress", 0.0) < UNREAD_PROGRESS_THRESHOLD
    ]
    # oldest saved first, matches reading order
    targets.sort(key=lambda b: b.get("time", 0))

    articles = []
    for b in targets:
        text_body = urllib.parse.urlencode({"bookmark_id": b["bookmark_id"]})
        resp2, content2 = None, None
        for attempt in range(3):
            resp2, content2 = client.request(TEXT_URL, method="POST", body=text_body)
            if resp2.status == 200:
                break
            time.sleep(2 * (attempt + 1))
        if resp2.status != 200:
            print(
                f"warning: get_text failed for {b['bookmark_id']}: {resp2.status}",
                file=sys.stderr,
            )
            continue
        articles.append(
            {
                "bookmark_id": b["bookmark_id"],
                "title": b.get("title", ""),
                "url": b.get("url", ""),
                "saved_time": b.get("time"),
                "text": clean_html(content2.decode()),
            }
        )

    return {
        "window_start_jst": window_start.isoformat(),
        "window_end_jst": window_end.isoformat(),
        "article_count": len(articles),
        "articles": articles,
    }


if __name__ == "__main__":
    result = fetch_articles()
    print(json.dumps(result, ensure_ascii=False, indent=2))
