# news_to_podcast

Daily (5:00 JST) pipeline: pulls Instapaper articles saved in the last 24
hours that are still unread, has Claude write a two-host Japanese dialogue
summary, synthesizes it with Google Cloud TTS, uploads the resulting audio
file to Google Drive, and prunes podcast audio older than 15 days.

Runs as a Claude Code cloud routine (see `ROUTINE_PROMPT.md`). No local
scheduler required.

## Pipeline steps (run daily by the routine)

1. `python src/fetch_instapaper.py > articles.json`
   Fetches unread bookmarks saved in the last 24 hours, pulls full article
   text, writes JSON.
2. The agent reads `articles.json` and writes `dialogue.json`: a JSON array
   of `{"speaker": "A"|"B", "text": "..."}` turns forming a natural
   two-host discussion covering every article.
3. `python src/synthesize.py dialogue.json podcast_YYYYMMDD.wav`
   Synthesizes each turn with Google Cloud TTS (fixed sample rate, WAV
   concatenation via stdlib `wave` -- no ffmpeg dependency) into one file,
   and logs the character count synthesized to `_usage_log.json` on Drive.
4. `python src/upload_drive.py podcast_YYYYMMDD.wav "Podcast YYYY-MM-DD"`
   Uploads to the configured Drive folder as the user's own account
   (OAuth), so the file is owned by the user.
5. `python src/cleanup_old_files.py`
   Deletes podcast audio (`podcast_*`, `audio/*` mime type only) older
   than 15 days from that same folder. Scoped tightly so it can never
   touch unrelated files (e.g. photos/videos) even by mistake.

## Usage/cost monitoring (run manually, not scheduled)

```
python src/check_usage.py
```

Reports this month's Google Cloud TTS character usage (self-logged, since
Cloud Monitoring access isn't required) against the combined
Neural2/Studio/Chirp3-HD free tier (1,000,000 chars/month), and the
user's actual Drive storage usage (reflects any paid Google One plan)
where the `drive.file` scope allows reading it.

## Cost notes

- Instapaper API: free.
- Summarization/dialogue writing: done by the routine's own reasoning
  (Claude) -- no separate paid API.
- Google Cloud TTS: free up to 1M chars/month (Neural2 used by default,
  cheaper than Chirp3-HD if that tier is ever exceeded: $16/$30 per 1M
  chars respectively). Requires a GCP billing account to be linked (won't
  be charged as long as usage stays under the free tier).
- Google Drive: uploads happen as the user's own account via OAuth (a
  bare service account has zero Drive storage quota and cannot own
  files at all), so storage is drawn from whatever plan the user already
  has (e.g. a paid Google One plan).

## One-time setup

1. Enable the Google Drive API on the GCP project.
2. Link a billing account to the GCP project (required for Cloud TTS).
3. Create a Drive folder for output in the user's own "My Drive"; copy
   its folder ID from the URL.
4. Configure the OAuth consent screen (External; Branding page filled in
   with an authorized domain + homepage/privacy links -- required by
   Google before publishing; a free GitHub Pages site works, see
   `docs/`); publish to "In production" (NOT "Testing", which revokes
   refresh tokens after 7 days); create an OAuth client ID of type
   "Desktop app".
5. Run `python scripts/oauth_setup.py <client_id> <client_secret>` once,
   locally, to get a refresh token (one-time interactive browser consent).
6. Store all secrets (see `config.example.env`) as environment secrets on
   the cloud routine.

## Required environment variables / secrets

See `config.example.env`. In the cloud routine these are set as
environment secrets (not embedded in the prompt):

- `INSTAPAPER_CONSUMER_KEY`, `INSTAPAPER_CONSUMER_SECRET`
- `INSTAPAPER_USERNAME`, `INSTAPAPER_PASSWORD`
- `GOOGLE_SERVICE_ACCOUNT_JSON` (full JSON key content, one line -- TTS only)
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN` (Drive)
- `GOOGLE_DRIVE_FOLDER_ID`
- `VOICE_A`, `VOICE_B` (optional, Google TTS voice names)

## Local testing

```
pip install -r requirements.txt
cp config.example.env .env   # fill in values, then export/source it
python src/fetch_instapaper.py > articles.json
```
