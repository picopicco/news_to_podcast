"""Synthesize a two-host dialogue script into a single podcast WAV file
using Google Cloud Text-to-Speech, and (optionally) upload it to Drive.

No ffmpeg/pydub dependency: audio is requested as LINEAR16 at a fixed
sample rate from both voices, and segments are concatenated with the
stdlib `wave` module.

Required env vars:
  GOOGLE_SERVICE_ACCOUNT_JSON   full JSON key content (not a file path)
  VOICE_A                       e.g. "ja-JP-Neural2-B" (defaults below)
  VOICE_B                       e.g. "ja-JP-Neural2-C" (defaults below)

Input: a JSON file with a list of turns:
  [{"speaker": "A", "text": "..."}, {"speaker": "B", "text": "..."}, ...]

Usage:
  python synthesize.py dialogue.json podcast_20260713.wav
"""
import datetime
import io
import json
import os
import sys
import wave

from google.cloud import texttospeech
from google.oauth2 import service_account

import drive_common

SAMPLE_RATE_HZ = 24000
SILENCE_MS_BETWEEN_TURNS = 350

DEFAULT_VOICES = {
    "A": os.environ.get("VOICE_A", "ja-JP-Neural2-B"),
    "B": os.environ.get("VOICE_B", "ja-JP-Neural2-C"),
}


def get_credentials():
    raw = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(raw)
    return service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )


def synthesize_turn(client, text, voice_name):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP",
        name=voice_name,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLE_RATE_HZ,
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    return response.audio_content  # WAV bytes (RIFF header included)


def silence_frames(ms, sample_width, n_channels):
    n_frames = int(SAMPLE_RATE_HZ * ms / 1000)
    return b"\x00" * (n_frames * sample_width * n_channels)


def build_podcast(turns, out_path):
    creds = get_credentials()
    client = texttospeech.TextToSpeechClient(credentials=creds)

    out_wav = wave.open(out_path, "wb")
    header_written = False
    sample_width = None
    n_channels = None
    total_chars = 0

    for i, turn in enumerate(turns):
        speaker = turn["speaker"]
        voice_name = DEFAULT_VOICES.get(speaker, DEFAULT_VOICES["A"])
        wav_bytes = synthesize_turn(client, turn["text"], voice_name)
        total_chars += len(turn["text"])

        with wave.open(io.BytesIO(wav_bytes), "rb") as seg:
            if not header_written:
                n_channels = seg.getnchannels()
                sample_width = seg.getsampwidth()
                out_wav.setnchannels(n_channels)
                out_wav.setsampwidth(sample_width)
                out_wav.setframerate(seg.getframerate())
                header_written = True
            out_wav.writeframes(seg.readframes(seg.getnframes()))

        if i < len(turns) - 1:
            out_wav.writeframes(
                silence_frames(SILENCE_MS_BETWEEN_TURNS, sample_width, n_channels)
            )

        print(f"synthesized turn {i + 1}/{len(turns)} ({speaker})", file=sys.stderr)

    out_wav.close()
    return total_chars


def log_tts_usage(chars):
    """Append today's TTS character count to _usage_log.json in the Drive
    folder, so check_usage.py can report cumulative monthly usage without
    needing Cloud Monitoring access. Best-effort: never fails the run."""
    try:
        token = drive_common.get_token()
        log = drive_common.download_json(token, "_usage_log.json", default={"tts_chars": []})
        log.setdefault("tts_chars", []).append(
            {"date": datetime.date.today().isoformat(), "chars": chars}
        )
        drive_common.upload_json(token, "_usage_log.json", log)
    except Exception as e:
        print(f"warning: failed to log usage: {e}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: synthesize.py dialogue.json out.wav", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        turns = json.load(f)

    chars = build_podcast(turns, sys.argv[2])
    log_tts_usage(chars)
    print(f"wrote {sys.argv[2]} ({chars} chars synthesized)", file=sys.stderr)
