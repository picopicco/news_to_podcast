"""One-time, local, interactive helper to obtain a Google OAuth refresh
token for the user's own account (Drive access). Not part of the daily
pipeline -- run this once on your own machine, then store the printed
refresh token as a secret for the cloud routine.

Prerequisites:
  1. In Google Cloud Console > APIs & Services > OAuth consent screen:
     - User type: External
     - Publishing status: "In production" (NOT "Testing" -- Testing
       apps get their refresh tokens revoked after 7 days)
  2. In APIs & Services > Credentials: create an OAuth client ID of type
     "Desktop app". Note its Client ID and Client Secret.

Usage:
  python scripts/oauth_setup.py <client_id> <client_secret>

A browser window opens for you to sign in and consent (you'll see an
"unverified app" warning -- click Advanced > Go to <app name> (unsafe);
this is expected and safe since it's your own app and your own account).
The refresh token is printed at the end.
"""
import http.server
import sys
import threading
import urllib.parse
import webbrowser

import requests

SCOPES = (
    "https://www.googleapis.com/auth/drive.file "
    "https://www.googleapis.com/auth/drive.metadata.readonly"
)
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    code = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            _CallbackHandler.code = params["code"][0]
            body = b"<html><body>Authorized. You can close this tab.</body></html>"
        else:
            body = b"<html><body>No code received.</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # silence default request logging


def main():
    if len(sys.argv) != 3:
        print("usage: oauth_setup.py <client_id> <client_secret>", file=sys.stderr)
        sys.exit(1)
    client_id, client_secret = sys.argv[1], sys.argv[2]

    server = http.server.HTTPServer(("127.0.0.1", 0), _CallbackHandler)
    port = server.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}/"

    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    print(f"Opening browser for authorization:\n{auth_url}\n", file=sys.stderr)
    webbrowser.open(auth_url)

    thread = threading.Thread(target=server.handle_request)
    thread.start()
    thread.join(timeout=300)

    if not _CallbackHandler.code:
        print("Timed out waiting for authorization.", file=sys.stderr)
        sys.exit(1)

    resp = requests.post(
        TOKEN_URL,
        data={
            "code": _CallbackHandler.code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    tokens = resp.json()

    if "refresh_token" not in tokens:
        print(
            "No refresh_token in response -- you may have already granted "
            "consent before. Revoke access at https://myaccount.google.com/permissions "
            "and re-run this script.",
            file=sys.stderr,
        )
        print(tokens, file=sys.stderr)
        sys.exit(1)

    print("\n=== Success ===")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={tokens['refresh_token']}")


if __name__ == "__main__":
    main()
