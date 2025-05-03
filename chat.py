import streamlit as st
import re
import db_manager

def display_chat_messages(messages):
    """Display chat messages with proper formatting"""
    if not messages:
        st.info("Start a conversation by typing a message below.")
        return
    
    # Display chat messages
    for message in messages:
        with st.chat_message(message["role"]):
            format_message_content(message["content"])

def format_message_content(content):
    """Format the message content with proper styling"""
    # Check if the content contains code blocks
    if "```" in content:
        # Split by code blocks
        parts = re.split(r'```(?:\w+)?\n|```', content)
        
        # Track if we're inside a code block
        is_code = False
        
        for part in parts:
            if part.strip():
                if is_code:
                    # Show as code block
                    st.code(part.strip())
                else:
                    # Show as regular text
                    st.write(part)
            
            # Toggle the code block state
            is_code = not is_code
    else:
        # Regular content
        st.write(content)

def clear_chat_history(agent_name):
    """Clear chat history for a specific agent and current conversation"""
    if agent_name in st.session_state.chat_history:
        # Get current conversation ID
        current_conv_id = st.session_state.current_conversation_id.get(agent_name)
        if current_conv_id and current_conv_id in st.session_state.chat_history[agent_name]:
            # Clear just the current conversation
            st.session_state.chat_history[agent_name][current_conv_id] = []
            
            # Save empty chat history to database
            if st.session_state.authenticated and st.session_state.username:
                db_manager.save_chat_history(
                    st.session_state.username,
                    agent_name,
                    current_conv_id,
                    []
                )