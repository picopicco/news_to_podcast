This is the exact prompt text used for the daily cloud routine.
Kept in the repo so it stays versioned alongside the code it drives.

---

You are running the daily news_to_podcast pipeline. The repo is already
checked out in the working directory. Do the following, in order, and
stop immediately with a clear error report if any step fails.

1. Install dependencies: `pip install -r requirements.txt`

2. Fetch today's articles:
   `python src/fetch_instapaper.py > articles.json`
   This pulls Instapaper bookmarks that were saved in the last 24 hours
   and are still unread (progress < 1.0, folder_id=unread).

3. Read articles.json.
   - If `article_count` is 0: stop here and report "no unread articles
     saved in the last 24 hours, nothing to synthesize" -- do not run
     steps 4-7.
   - Otherwise continue.

4. Write `dialogue.json`: a JSON array of turns, each
   `{"speaker": "A", "text": "..."}` or `{"speaker": "B", "text": "..."}`,
   forming a natural two-host Japanese podcast conversation that covers
   every article in articles.json. Guidelines:
   - Speaker A is the main host (progresses the show, introduces topics).
     Speaker B is the co-host (reacts, asks questions, adds color).
   - Open with a short greeting ("Today is <date>, here are N articles
     from your Instapaper unread list..."). Close with a short sign-off.
   - For each article: introduce the title/topic naturally, summarize the
     content without skipping important substance (this is a full
     summary, not a teaser), and let the hosts briefly discuss or react
     before moving to the next article.
   - Natural spoken Japanese (です/ます or casual, pick one style and stay
     consistent), no markdown, no bullet points, no emoji -- this text is
     fed directly to TTS.
   - Each turn's `text` should be a few sentences at most (TTS is called
     once per turn); split long segments into multiple alternating turns
     rather than one huge block.

5. Synthesize the audio:
   `python src/synthesize.py dialogue.json podcast_<window_end_date>.wav`
   (use the `window_end_jst` date from articles.json, formatted YYYYMMDD)
   This also logs the characters synthesized to `_usage_log.json` on
   Drive for later cost monitoring.

6. Upload to Drive:
   `python src/upload_drive.py podcast_<window_end_date>.wav "Podcast <YYYY-MM-DD>"`

7. Clean up old audio:
   `python src/cleanup_old_files.py`
   Deletes podcast audio older than 15 days from the same Drive folder.
   This only ever touches files named `podcast_*` with an audio mime
   type, so it cannot affect unrelated files such as photos or videos.

8. Report a short summary: number of articles covered, their titles, the
   Drive file id/name from the upload response, and how many old files
   (if any) were deleted in step 7.
