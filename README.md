# AgriLingo

Multilingual Sensor-Aware Conversational Agriculture Assistant.

## Setup

Create `.env` in the project root:

```env
GEMINI_API_KEY=your-gemini-key
DEEPGRAM_API_KEY=your-deepgram-key
FLASK_SECRET_KEY=use-a-random-local-secret
```

Install the Python dependencies and run Flask:

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

The application requires microphone permission in the browser. Deepgram and
gTTS require network access when a voice request is processed.

## Voice pipeline

The dashboard records audio with `MediaRecorder` and posts it to `/speech`.
The server then performs Tamil Deepgram STT, Tamil-to-English Gemini
translation, the English RAG call, English-to-Tamil Gemini translation, and
Tamil gTTS. The response includes each text stage and base64-encoded MP3 audio
for immediate browser playback.

## RAG integration point

Replace only `rag_query(english_text)` in `app.py`. It must accept one English
string and return one English string. The `/speech` route handles the rest of
the voice pipeline and does not need to change when the real RAG implementation
is added.
