from dotenv import load_dotenv
from google import genai
import streamlit as st
import os


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

st.title("My First AI Chatbot")

question = st.text_input("Ask a question")

if question:
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=question
    )

    st.write(response.text)