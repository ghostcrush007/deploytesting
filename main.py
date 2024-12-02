import streamlit as st
from groq import Groq
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Initialize Groq client
client = Groq(api_key=api_key)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []  # Initialize as an empty list

# Streamlit UI setup
st.title("MY-BOT")
st.markdown("A simple chatbot interface powered by Groq console")

# Display conversation in ChatGPT-like format
chat_placeholder = st.empty()  # Placeholder for dynamic rendering

# Function to render the conversation
def render_conversation():
    with chat_placeholder.container():
        for i, msg in enumerate(st.session_state.messages):
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            elif msg["role"] == "assistant":
                st.markdown(f"**Assistant:** {msg['content']}")

# Display the conversation initially
render_conversation()

# Get user input
user_input = st.text_input("Ask something:", key="input")

# Handle user input
if user_input:
    # Add user input to session state
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Render updated conversation
    render_conversation()

    # Get response from the model
    completion = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=st.session_state.messages,
        temperature=0.5,
        max_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )
    response = completion.choices[0].message.content

    # Add assistant response to session state
    st.session_state.messages.append({"role": "assistant", "content": response})

    # Render updated conversation
    render_conversation()
