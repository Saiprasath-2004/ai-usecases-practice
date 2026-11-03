from google import genai
from dotenv import load_dotenv

import os

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

while True:
    question = input("Ask a question (or type 'exit' to quit): ")

    if question.lower() == 'exit':
        break
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=question
    )
    print("\nAI: " + response.text)
    