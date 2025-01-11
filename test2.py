import streamlit as st
from groq import Groq
import os
from dotenv import load_dotenv
import sounddevice as sd
from scipy.io.wavfile import write
import sqlite3
import json
from datetime import datetime
from fpdf import FPDF

# Load environment variables
load_dotenv()
api_key = "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"

# Initialize Groq client
client = Groq(api_key=api_key)

# Constants for audio recording
audio_file = "audio.wav"
duration = 5  # Default duration for recording
sample_rate = 44100

# Database setup
conn = sqlite3.connect("chat_history.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    messages TEXT
)
""")
conn.commit()

# CSS for High-Contrast Mode
high_contrast_css = """
<style>
    body {
        background-color: #000000 !important;
        color: #FFFFFF !important;
    }
    .stButton > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #FFFFFF !important;
    }
    .stTextInput > div > div > input {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
    }
    .stMarkdown, .stMarkdown p {
        background-color: #000000 !important;
        color: #FFFFFF !important;
    }
</style>
"""
# apply by default
st.markdown(high_contrast_css, unsafe_allow_html=True)
# # High-Contrast Mode Toggle
# # if "high_contrast" not in st.session_state:
# #     st.session_state.high_contrast = True

# # if st.checkbox("Enable High-Contrast Mode"):
# #     st.session_state.high_contrast = True
# #     st.markdown(high_contrast_css, unsafe_allow_html=True)
# # else:
# #     st.session_state.high_contrast = False

# # CSS to apply background image to the entire app
# background_image_css = """
# <style>
#     body {
#         background-image: url('https://i.pinimg.com/736x/c8/5a/2a/c85a2a1152957135ad2bcd2816decd49.jpg')
#         background-size: cover;
#         background-position: center center;
#         background-attachment: fixed;
#         color: #FFFFFF !important;
#     }
#     .stButton > button {
#         background-color: #FFFFFF !important;
#         color: #000000 !important;
#         border: 2px solid #FFFFFF !important;
#     }
#     .stTextInput > div > div > input {
#         background-color: #000000 !important;
#         color: #FFFFFF !important;
#         border: 1px solid #FFFFFF !important;
#     }
#     .stMarkdown, .stMarkdown p {
#         background-color: rgba(0, 0, 0, 0.5) !important;  /* Semi-transparent background for better readability */
#         color: #FFFFFF !important;
#     }
# </style>
# """

# # Apply the background image and styling
# st.markdown(background_image_css, unsafe_allow_html=True)

    
# Save conversation to database
def save_conversation(messages):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO chat_history (timestamp, messages) VALUES (?, ?)", (timestamp, json.dumps(messages)))
    conn.commit()

# Load all conversations from database
def load_conversations():
    cursor.execute("SELECT id, timestamp FROM chat_history ORDER BY id DESC")
    return cursor.fetchall()

# Load a specific conversation
def load_conversation(conversation_id):
    cursor.execute("SELECT messages FROM chat_history WHERE id = ?", (conversation_id,))
    return json.loads(cursor.fetchone()[0])

# Reset chat state
def reset_chat():
    st.session_state.messages = []
    st.session_state.uploaded_content = ""
    # Reset query parameters to ensure fresh start
    st.query_params = {}

def delete_chat_history():
    cursor.execute("DELETE FROM chat_history")
    conn.commit()
    st.query_params = {}

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "recording" not in st.session_state:
    st.session_state.recording = False
if "transcribed_text" not in st.session_state:
    st.session_state.transcribed_text = ""
if "uploaded_content" not in st.session_state:
    st.session_state.uploaded_content = ""

# Streamlit UI setup
st.title("MY-BOT 🦙")
st.markdown("A chatbot interface with text, voice, and file input powered by Groq Console.")

# Display "New Chat" button on the main page
if st.button("🆕 New Chat"):
    if st.session_state.messages:
        save_conversation(st.session_state.messages)
    reset_chat()
    # Refresh the page by setting query parameters (resets session state)
    st.query_params = {}

# Sidebar for chat history
st.sidebar.title("Chat History")
if st.sidebar.button("🗑️ Delete Chat History"):
    delete_chat_history()
    st.sidebar.success("Chat history deleted successfully!")
    reset_chat()  # Reset current session state

conversations = load_conversations()
if conversations:
    for conv_id, timestamp in conversations:
        if st.sidebar.button(f"Conversation {conv_id} - {timestamp}"):
            st.session_state.messages = load_conversation(conv_id)
            st.success(f"Loaded Conversation {conv_id} from {timestamp}")

# Display conversation
chat_placeholder = st.empty()

def render_conversation():
    with chat_placeholder.container():
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(
                    f"""
                    <div style="background-color: #f0f0f0; color: black; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                        <strong>You:</strong> {msg['content']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            elif msg["role"] == "assistant":
                st.markdown(
                    f"""
                    <div style="background-color: #d4f5d4; color: black; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                        <strong>Assistant:</strong> {msg['content']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

render_conversation()

# Voice recording functions
def start_recording():
    st.session_state.recording = True
    st.write("Recording started...")
    st.session_state.recorded_audio = sd.rec(
        int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16"
    )
    sd.wait()
    st.session_state.recording = False
    write(audio_file, sample_rate, st.session_state.recorded_audio)
    st.session_state.transcribed_text = transcribe_audio()

def transcribe_audio():
    with open(audio_file, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=(audio_file, file.read()),
            model="distil-whisper-large-v3-en",
            response_format="verbose_json",
        )
    st.session_state.transcribed_text = transcription.text
    return transcription.text

# Handle user input and bot response
def handle_bot_response(user_input):
    # Add uploaded content as context to the conversation (if any)
    if st.session_state.uploaded_content:
        st.session_state.messages.append({"role": "system", "content": f"Content from file: {st.session_state.uploaded_content}"})
        st.session_state.uploaded_content = ""  # Clear after use

    st.session_state.messages.append({"role": "user", "content": user_input})
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=st.session_state.messages,
        temperature=0.5,
        max_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )
    response = completion.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": response})
    render_conversation()

# Input form for text and voice
st.markdown(
    """
    <style>
    .chat-input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: white;
        padding: 10px;
        box-shadow: 0px -2px 5px rgba(0, 0, 0, 0.1);
        z-index: 1000;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)

# Text input form
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input("Ask something:", key="input")
    submit_button = st.form_submit_button("Submit")

st.markdown('</div>', unsafe_allow_html=True)

# File upload functionality
uploaded_file = st.file_uploader("Upload a text file", type=["txt", "pdf", "docx"])

if uploaded_file:
    file_content = uploaded_file.read().decode("utf-8")  # Decode the uploaded file content as text
    st.session_state.uploaded_content = file_content  # Store the content
    st.write("File content successfully uploaded:")
    st.write(st.session_state.uploaded_content)  # Show the content for debugging

# Recording controls
if st.button("🎙️ Start Recording") and not st.session_state.recording:
    start_recording()
    handle_bot_response(st.session_state.transcribed_text)

# Handle text input
if submit_button and user_input:
    handle_bot_response(user_input)

def download_chat_as_text(messages):
    chat_content = "\n".join(
        f"{'You' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}" for msg in messages
    )
    st.download_button(
        label="Download Chat as Text",
        data=chat_content,
        file_name="chat_history.txt",
        mime="text/plain",
    )

def download_chat_as_pdf(messages):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Chat History", ln=True, align="C")
    pdf.ln(10)
    for msg in messages:
        role = "You" if msg["role"] == "user" else "Assistant"
        pdf.multi_cell(0, 10, f"{role}: {msg['content']}")
    pdf_output = pdf.output(dest="S").encode("latin1")
    st.download_button(
        label="Download Chat as PDF",
        data=pdf_output,
        file_name="chat_history.pdf",
        mime="application/pdf",
    )

if st.session_state.messages:
    st.subheader("Download Chat History")
    download_chat_as_text(st.session_state.messages)
    download_chat_as_pdf(st.session_state.messages)