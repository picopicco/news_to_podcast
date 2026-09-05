"""Turn fetched articles into a two-host Japanese podcast dialogue script
using the Gemini API (free tier, separate from Cloud Billing).

Required env vars:
  GEMINI_API_KEY
  GEMINI_MODEL   optional, defaults to gemini-3.6-flash

Usage:
  python summarize.py articles.json dialogue.json
"""
import json
import os
import sys

import requests

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "speaker": {"type": "STRING", "enum": ["A", "B"]},
            "text": {"type": "STRING"},
        },
        "required": ["speaker", "text"],
    },
}

PROMPT_TEMPLATE = """あなたは日本語ポッドキャストの台本作家です。以下の記事すべてを取り上げる、
2人のホストによる自然な会話形式の台本を作成してください。

出力形式: {{"speaker": "A"または"B", "text": "..."}} のオブジェクトを並べたJSON配列のみ。
説明文やマークダウンは一切含めないでください。

構成のガイドライン:
- 話者Aがメインの進行役、話者Bが相槌・質問・感想を担当する聞き役です。
- 冒頭で簡単な挨拶(日付、記事が{count}件あることに触れる)。締めくくりも簡単に。
- 各記事について、タイトル・話題を自然に紹介し、内容を大事な部分を端折らずに
  要約し、2人で短く感想や議論を交わしてから次の記事に移ってください。
- 自然な話し言葉の日本語(です/ます調で統一)。箇条書き・記号・絵文字は使わない
  (音声合成にそのまま読み上げられます)。
- 1ターンのtextは数文程度まで。長い内容は複数ターンに分割してください。

対象日: {date}
記事一覧:
{articles_text}
"""


def build_prompt(articles, date):
    parts = []
    for a in articles:
        parts.append(f"### {a['title']}\nURL: {a['url']}\n\n{a['text']}")
    articles_text = "\n\n---\n\n".join(parts)
    return PROMPT_TEMPLATE.format(count=len(articles), date=date, articles_text=articles_text)


def generate_dialogue(articles, date):
    api_key = os.environ["GEMINI_API_KEY"]
    prompt = build_prompt(articles, date)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
        },
    }
    resp = requests.post(f"{API_URL}?key={api_key}", json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API failed: {resp.status_code} {resp.text}")

    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: summarize.py articles.json dialogue.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)

    dialogue = generate_dialogue(data["articles"], data["window_end_jst"][:10])

    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(dialogue, f, ensure_ascii=False, indent=2)

    print(f"wrote {sys.argv[2]} ({len(dialogue)} turns)", file=sys.stderr)
