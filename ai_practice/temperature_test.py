from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


question = "Write one sentence about the ocean."

for temperature in [0, 0.5, 1]:
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=question,
        config={
            "temperature": temperature
        }
    )

    print("=" * 50)
    print(f"Temperature: {temperature}")
    print(response.text)