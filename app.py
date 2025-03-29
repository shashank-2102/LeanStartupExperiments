import streamlit as st
import random
import time
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
import dotenv
import os
import pandas as pd

dotenv.load_dotenv()

# Define the Google Sheet URL
url = "https://docs.google.com/spreadsheets/d/162fk4EmAOdHTkt0xDOcXgrefNwtWb5Ms1z-weLpsZ8Q/edit?usp=sharing"

# Initialize connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)


existing_data = conn.read(spreadsheet=url, worksheet="conversations")
if existing_data is None or existing_data.empty:
    existing_data = pd.DataFrame(columns=["Prompt", "Response"])

st.title("Business Model Canvas")

# Set OpenAI API key from Streamlit secrets
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Set a default model
if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-4o-mini-2024-07-18"

# Define the system message with instructions
business_model_canvas_instructions = """
You are a Business Model Canvas expert assistant. Your primary purpose is to help users create and refine their business model canvas.

When asked about a business or business idea, always structure your responses using the 9 components of the Business Model Canvas:

1. Customer Segments: Who are the customers? What are their needs?
2. Value Propositions: What value do you deliver to customers? Which problems do you solve?
3. Channels: How do you reach your customers? Through which channels?
4. Customer Relationships: What type of relationship do you establish with customers?
5. Revenue Streams: How does the business earn money from each customer segment?
6. Key Resources: What key assets are required to make the business model work?
7. Key Activities: What key activities does the business need to perform?
8. Key Partnerships: Who are your key partners and suppliers?
9. Cost Structure: What are the most important costs in your business model?

For each component, provide specific, actionable suggestions based on the user's business or idea. Be concise but thorough. Use formatting to make your response easy to read.

If details are missing, ask clarifying questions to help complete the canvas.
"""

# Initialize chat history with system message (hidden from user view)
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": business_model_canvas_instructions}
    ]

# Display chat messages from history on app rerun (skip system messages)
for message in st.session_state.messages:
    if message["role"] != "system":  # Don't show system messages to the user
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Ask me about creating a Business Model Canvas for your idea"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )
        response = st.write_stream(stream)
    
    # Add assistant message to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Create a new row with the conversation
    new_row = pd.DataFrame({"Prompt": [prompt], "Response": [response]})
    
    # Append the new row to existing data
    updated_data = pd.concat([existing_data, new_row], ignore_index=True)

    conn.update(spreadsheet=url, worksheet="conversations", data=updated_data)
