import base64
import io
import os

import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from google import genai
from dotenv import dotenv_values
from gtts import gTTS


# =========================================================
# LOAD .ENV
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENV_PATH = os.path.join(BASE_DIR, ".env")

config = dotenv_values(ENV_PATH)

api_key = config.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY not found in .env"
    )


deepgram_api_key = config.get("DEEPGRAM_API_KEY")

if not deepgram_api_key:
    raise RuntimeError(
        "DEEPGRAM_API_KEY not found in .env"
    )

# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "agrilingo-secret-key")


# =========================================================
# GEMINI
# =========================================================

client = genai.Client(
    api_key=api_key
)


# =========================================================
# TEMPORARY USER STORAGE
# =========================================================

users = {}


def translate_text(text, source_language, target_language):
    """Translate text with Gemini and return only the translated text."""
    prompt = f"""
Translate the following text from {source_language} to {target_language}.
Return only the translation, with no explanation, labels, quotation marks, or
additional formatting.

Text:
{text}
"""
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
    )
    translated = (response.text or "").strip()
    if not translated:
        raise ValueError("Gemini returned an empty translation")
    return translated


def rag_query(english_text):
    """Temporary RAG contract: accept English and return English.

    Replace only this function with the real retrieval and generation logic.
    The /speech route and all microphone, translation, and TTS code can remain
    unchanged as long as the replacement returns a string.
    """
    return (
        "Your crop's water requirement depends on the crop type, soil condition, "
        "temperature, and current moisture level."
    )


def transcribe_tamil(audio_data, content_type):
    response = requests.post(
        "https://api.deepgram.com/v1/listen",
        params={"model": "nova-3", "language": "ta", "smart_format": "true"},
        headers={
            "Authorization": f"Token {deepgram_api_key}",
            "Content-Type": content_type or "audio/webm",
        },
        data=audio_data,
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError("Deepgram could not process the audio")
    result = response.json()
    return (
        result.get("results", {})
        .get("channels", [{}])[0]
        .get("alternatives", [{}])[0]
        .get("transcript", "")
        .strip()
    )


def synthesize_tamil(text):
    audio_buffer = io.BytesIO()
    gTTS(text=text, lang="ta").write_to_fp(audio_buffer)
    return audio_buffer.getvalue()


# =========================================================
# LANDING PAGE
# =========================================================

@app.route("/")
def home():

    return render_template("landing.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username in users and users[username] == password:

            session["username"] = username

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


# =========================================================
# SIGNUP
# =========================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username in users:

            return render_template(
                "signup.html",
                error="Username already exists"
            )

        users[username] = password

        return redirect(url_for("login"))

    return render_template("signup.html")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "username" not in session:

        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["username"]
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =========================================================
# GEMINI CHAT
# =========================================================

@app.route("/chat", methods=["POST"])
def chat():

    # Make sure user is logged in

    if "username" not in session:

        return jsonify({
            "error": "You must be logged in."
        }), 401


    # Get JSON from frontend

    data = request.get_json()

    if not data:

        return jsonify({
            "error": "No message received."
        }), 400


    # Get user's message

    user_message = data.get(
        "message",
        ""
    ).strip()


    # Don't allow empty messages

    if not user_message:

        return jsonify({
            "error": "Please enter a message."
        }), 400


    # =====================================================
    # AGRILINGO PROMPT
    # =====================================================

    prompt = f"""
You are AgriLingo, an agricultural assistant designed
to help farmers.

Give clear, practical and easy-to-understand answers.

You can help with:

- Soil moisture
- Humidity
- Temperature
- Irrigation
- Crop health
- Farming practices
- Basic agricultural concepts

IMPORTANT:

AgriLingo currently does NOT have live sensor data.

Do not pretend that you have sensor readings.

If the farmer asks about their current farm conditions,
explain that live sensor data is not available yet.

Farmer's question:

{user_message}
"""


    # =====================================================
    # ASK GEMINI
    # =====================================================

    try:

        response = client.models.generate_content(

            model="gemini-3.1-flash-lite",

            contents=prompt

        )


        return jsonify({
            "response": response.text
        })


    except Exception as e:

        print("GEMINI ERROR:", e)

        return jsonify({
            "error": "Gemini could not process the request."
        }), 500


# =========================================================
# VOICE PIPELINE
# =========================================================

@app.route("/speech", methods=["POST"])
def speech():
    if "username" not in session:
        return jsonify({"error": "You must be logged in."}), 401

    audio = request.files.get("audio")
    if audio is None or not audio.filename:
        return jsonify({"error": "No audio received."}), 400

    audio_data = audio.read()
    if not audio_data:
        return jsonify({"error": "The recorded audio is empty."}), 400

    try:
        tamil_transcript = transcribe_tamil(audio_data, audio.content_type)
        if not tamil_transcript:
            return jsonify({"error": "No Tamil speech was detected."}), 400

        english_translation = translate_text(
            tamil_transcript,
            "Tamil",
            "English",
        )
        english_rag_response = rag_query(english_translation)
        if not isinstance(english_rag_response, str) or not english_rag_response.strip():
            raise ValueError("RAG returned an empty or invalid response")

        tamil_response = translate_text(
            english_rag_response,
            "English",
            "Tamil",
        )
        audio_output = synthesize_tamil(tamil_response)

        return jsonify({
            "transcript": tamil_transcript,
            "english_translation": english_translation,
            "rag_response": english_rag_response,
            "tamil_response": tamil_response,
            "audio": base64.b64encode(audio_output).decode("ascii"),
            "audio_mime_type": "audio/mpeg",
        })
    except requests.RequestException:
        app.logger.exception("Deepgram request error")
        return jsonify({"error": "Speech transcription service is unavailable."}), 502
    except Exception as error:
        app.logger.exception("Speech pipeline error: %s", error)
        return jsonify({"error": "Unable to complete the voice response."}), 500


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
