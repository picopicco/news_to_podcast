# news_to_podcast

Daily (5:00 JST) pipeline: pulls Instapaper articles saved in the last 24
hours that are still unread, has Gemini write a two-host Japanese
dialogue summary, synthesizes it with Google Cloud TTS, uploads the
resulting audio file to Google Drive, and prunes podcast audio older
than 15 days.

Runs locally via Windows Task Scheduler (see `docs/task_scheduler.md`).
A cloud-hosted version was attempted first but abandoned: Claude Code
cloud routines run behind a fixed network egress allowlist that cannot
be extended to reach Instapaper or Google's APIs, so the pipeline could
never actually run there.

## Pipeline (run daily by `run_pipeline.py`)

1. `src/fetch_instapaper.py` -- fetches unread bookmarks saved in the
   last 24 hours, pulls full article text, writes `articles.json`.
2. `src/summarize.py` -- sends the articles to the Gemini API, which
   returns a two-host Japanese dialogue script (`dialogue.json`): a JSON
   array of `{"speaker": "A"|"B", "text": "..."}` turns covering every
   article.
3. `src/synthesize.py` -- synthesizes each turn with Google Cloud TTS
   (fixed sample rate, WAV concatenation via stdlib `wave` -- no ffmpeg
   dependency) into one file, and logs the character count synthesized
   to `_usage_log.json` on Drive.
4. `src/upload_drive.py` -- uploads to the configured Drive folder as
   the user's own account (OAuth), so the file is owned by the user.
5. `src/cleanup_old_files.py` -- deletes podcast audio (`podcast_*`,
   `audio/*` mime type only) older than 15 days from that same folder.
   Scoped tightly so it can never touch unrelated files (e.g.
   photos/videos) even by mistake.

`run_pipeline.py` orchestrates all five steps and is what Task Scheduler
runs once a day; it loads credentials from a local `.env` file.

## Usage/cost monitoring (run manually, not scheduled)

```
python src/check_usage.py
```

Reports this month's Google Cloud TTS character usage (self-logged)
against the combined Neural2/Studio/Chirp3-HD free tier (1,000,000
chars/month), and the user's Drive storage usage where the `drive.file`
scope allows reading it.

## Cost notes

- Instapaper API: free.
- Summarization/dialogue writing: Gemini API free tier (separate from
  Cloud Billing; rate-limited but ample for one run/day).
- Google Cloud TTS: free up to 1M chars/month (Neural2 used by default,
  cheaper than Chirp3-HD if that tier is ever exceeded: $16/$30 per 1M
  chars respectively). Requires a GCP billing account to be linked (won't
  be charged as long as usage stays under the free tier).
- Google Drive: uploads happen as the user's own account via OAuth (a
  bare service account has zero Drive storage quota and cannot own
  files at all), so storage is drawn from whatever plan the user
  already has (e.g. a paid Google One plan).

## One-time setup

1. Enable the Google Drive API on the GCP project.
2. Link a billing account to the GCP project (required for Cloud TTS).
3. Get a Gemini API key at https://aistudio.google.com/apikey.
4. Create a Drive folder for output in the user's own "My Drive"; copy
   its folder ID from the URL.
5. Configure the OAuth consent screen (External; Branding page filled in
   with an authorized domain + homepage/privacy links -- a free GitHub
   Pages site works, see `docs/`); publish to "In production" (NOT
   "Testing", which revokes refresh tokens after 7 days); create an
   OAuth client ID of type "Desktop app".
6. Run `python scripts/oauth_setup.py <client_id> <client_secret>` once,
   locally, to get a refresh token (one-time interactive browser consent).
7. Copy `config.example.env` to `.env` in the repo root and fill in every
   value.
8. Set up the Windows Task Scheduler job -- see `docs/task_scheduler.md`.

## Required environment variables

See `config.example.env`. `run_pipeline.py` loads these from a local
`.env` file (never commit the real `.env`):

- `INSTAPAPER_CONSUMER_KEY`, `INSTAPAPER_CONSUMER_SECRET`
- `INSTAPAPER_USERNAME`, `INSTAPAPER_PASSWORD`
- `GEMINI_API_KEY` (summarization)
- `GOOGLE_SERVICE_ACCOUNT_JSON` (full JSON key content, one line -- TTS only)
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN` (Drive)
- `GOOGLE_DRIVE_FOLDER_ID`
- `VOICE_A`, `VOICE_B` (optional, Google TTS voice names)

## Manual run

```
pip install -r requirements.txt
python run_pipeline.py
```
