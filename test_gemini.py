from google import genai
import os

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

response = client.models.generate_content(
    model="gemini-3.1-flash-lite",
    contents="Explain soil moisture to a farmer in one sentence."
)

print(response.text)
