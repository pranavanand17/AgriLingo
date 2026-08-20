from flask import Flask, render_template, request, redirect, url_for, session
from google import genai
from dotenv import dotenv_values
import os


# =========================
# LOAD .ENV
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENV_PATH = os.path.join(BASE_DIR, ".env")

config = dotenv_values(ENV_PATH)

api_key = config.get("GEMINI_API_KEY")

print("Looking for .env at:", ENV_PATH)
print("Gemini API key loaded:", bool(api_key))


if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY not found in .env"
    )


# =========================
# FLASK
# =========================

app = Flask(__name__)

app.secret_key = "agrilingo-secret-key"


# =========================
# GEMINI
# =========================

client = genai.Client(
    api_key=api_key
)


# =========================
# TEMPORARY USER STORAGE
# =========================

users = {}


# =========================
# LANDING PAGE
# =========================

@app.route("/")
def home():

    return render_template("landing.html")


# =========================
# LOGIN
# =========================

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


# =========================
# SIGNUP
# =========================

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


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if "username" not in session:

        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["username"]
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =========================
# GEMINI CHAT
# =========================

@app.route("/chat", methods=["POST"])
def chat():

    # Make sure user is logged in

    if "username" not in session:

        return {
            "error": "You must be logged in."
        }, 401


    # Get JSON from frontend

    data = request.get_json()


    # Get user's message

    user_message = data.get("message", "").strip()


    # Don't allow empty messages

    if not user_message:

        return {
            "error": "Please enter a message."
        }, 400


    # =========================
    # AGRILINGO PROMPT
    # =========================

    prompt = f"""
You are AgriLingo, an agricultural assistant designed to help farmers.

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


    # =========================
    # ASK GEMINI
    # =========================

    try:

        response = client.models.generate_content(

            model="gemini-3.1-flash-lite",

            contents=prompt

        )


        return {
            "response": response.text
        }


    except Exception as e:

        print("GEMINI ERROR:", e)

        return {
            "error": "Gemini could not process the request."
        }, 500


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":

    app.run(debug=True)
