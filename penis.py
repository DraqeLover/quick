from google import genai
from Characters import FRIGGA
from dotenv import load_dotenv 
import os
load_dotenv("Key.env")

# Api key setup
GEMINI_API_KEY = os.getenv("GENAI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=FRIGGA + "hello",
)

print(response.text)
