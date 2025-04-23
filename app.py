import streamlit as st
import os
import db_manager
import auth
import chat
import agent as agent_module
import admin
import rag_system
from models import setup_database
import traceback
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Multi-Agent Chatbot System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.page = "chat"
    st.session_state.current_agent = None
    st.session_state.chat_history = {}
    st.session_state.show_agent_recommendation = False
    st.session_state.show_api_key_panel = False
    st.session_state.debug_mode = False  # Add debug mode flag
    st.session_state.waiting_for_response = False  # Track if we're waiting for a response
    st.session_state.new_message = None  # For storing new messages temporarily

# Initialize the database
try:
    setup_database()
except Exception as e:
    st.error(f"Error setting up database: {e}")
    st.info("Please make sure the database credentials are correctly set in the environment variables.")
    st.code(traceback.format_exc())

# Application header and sidebar
def render_sidebar():
    with st.sidebar:
        st.title("🤖 Multi-Agent Chat")
        
        if st.session_state.authenticated:
            st.write(f"Welcome, **{st.session_state.username}**!")
            
            # Navigation
            st.subheader("Navigation")
            nav_options = ["Chat"]
            
            # Add admin page for admin users
            if st.session_state.role == "admin":
                nav_options.append("Admin")
                
            selected_page = st.radio("Go to", nav_options)
            
            if selected_page == "Chat":
                st.session_state.page = "chat"
            elif selected_page == "Admin":
                st.session_state.page = "admin"
            
            # Agent selection
            if st.session_state.page == "chat":
                st.subheader("Select Agent")
                agents = db_manager.get_agents()
                
                if agents:
                    agent_names = [agent["name"] for agent in agents]
                    current_agent = st.selectbox(
                        "Choose your assistant:",
                        agent_names,
                        index=agent_names.index(st.session_state.current_agent) if st.session_state.current_agent in agent_names else 0
                    )
                    
                    if current_agent != st.session_state.current_agent:
                        st.session_state.current_agent = current_agent
                        st.rerun()
                    
                    # Display agent description
                    selected_agent = next((a for a in agents if a["name"] == current_agent), None)
                    if selected_agent:
                        st.markdown(f"**{selected_agent['description']}**")
                        
                    # Clear chat button
                    if st.button("Clear Chat"):
                        chat.clear_chat_history(st.session_state.current_agent)
                        st.rerun()
                        
                    # Show agent recommendations toggle
                    st.session_state.show_agent_recommendation = st.toggle(
                        "Show agent recommendations",
                        value=st.session_state.show_agent_recommendation
                    )
                else:
                    st.error("No agents found. Please contact an administrator.")
            
            # API Key Configuration Section
            st.subheader("API Configuration")
            api_key_button = st.button("📝 Configure OpenAI API Key")
            if api_key_button:
                st.session_state.show_api_key_panel = not st.session_state.show_api_key_panel
            
            # Debug mode toggle (for admins only)
            if st.session_state.role == "admin":
                st.session_state.debug_mode = st.toggle(
                    "Debug Mode", 
                    value=st.session_state.debug_mode,
                    help="Enable debug information"
                )
            
            # Logout button
            if st.button("Logout"):
                auth.logout()
                st.rerun()
        else:
            st.info("Please login or register to continue.")

# Function to process user input and get agent response
def process_message(user_input, agent_chat_history):
    # Add user message to chat history first - this will be displayed immediately
    agent_chat_history.append({"role": "user", "content": user_input})
    
    try:
        # Get the agent's system prompt
        agents = db_manager.get_agents()
        agent_info = next((a for a in agents if a["name"] == st.session_state.current_agent), None)
        
        if agent_info:
            system_prompt = agent_info["system_prompt"]
            
            # Set waiting flag to display the "Thinking..." message
            st.session_state.waiting_for_response = True
            
            # Get response from the agent
            response = agent_module.get_agent_response(user_input, system_prompt, agent_chat_history)
            
            # Add agent response to chat history
            agent_chat_history.append({"role": "assistant", "content": response})
            
            # Save chat history to database
            if st.session_state.authenticated and st.session_state.username:
                save_success = db_manager.save_chat_history(
                    st.session_state.username,
                    st.session_state.current_agent,
                    agent_chat_history
                )
                
                if st.session_state.debug_mode and not save_success:
                    st.warning("Failed to save chat history to database")
            
            # Reset waiting flag
            st.session_state.waiting_for_response = False
            
            # Return any recommendations if needed
            if st.session_state.show_agent_recommendation:
                return rag_system.get_agent_recommendations(user_input, 2)
            
            return None
    except Exception as e:
        # Add error message to chat history
        error_message = f"I'm sorry, I encountered an error: {str(e)}"
        agent_chat_history.append({"role": "assistant", "content": error_message})
        
        # Reset waiting flag
        st.session_state.waiting_for_response = False
        
        if st.session_state.debug_mode:
            return traceback.format_exc()
        
        return None

# Main application
def main():
    render_sidebar()
    
    if not st.session_state.authenticated:
        # Show authentication page
        auth.show_auth_page()
    else:
        # Show page based on selection
        if st.session_state.page == "chat":
            render_chat_page()
        elif st.session_state.page == "admin" and st.session_state.role == "admin":
            admin.show_admin_page()
        else:
            st.warning("Page not found or access denied.")

def render_chat_page():
    st.title(f"Chat with {st.session_state.current_agent}")
    
    # API Key Configuration Panel (shown/hidden based on session state)
    if st.session_state.show_api_key_panel:
        with st.expander("OpenAI API Key Configuration", expanded=True):
            st.warning("⚠️ You need to configure an OpenAI API key to use this chatbot. The API key is stored securely in the database.")
            
            # Get current configuration
            config = db_manager.get_config()
            current_api_key = config.get("openai_api_key", "")
            api_key_placeholder = "****************************" if current_api_key else "No API key set"
            
            # Show masked API key and option to update
            st.text_input("Current OpenAI API Key", value=api_key_placeholder, disabled=True)
            new_api_key = st.text_input("New OpenAI API Key", type="password", 
                                       help="Enter your OpenAI API key here. You can get one from https://platform.openai.com/api-keys")
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("Save API Key"):
                    if new_api_key:
                        try:
                            # Update config in database
                            config["openai_api_key"] = new_api_key
                            db_manager.update_config(config)
                            st.success("API key updated successfully!")
                            # Hide the panel after successful update
                            st.session_state.show_api_key_panel = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating API key: {e}")
            with col2:
                if st.button("Close Panel"):
                    st.session_state.show_api_key_panel = False
                    st.rerun()
    
    # Initialize chat history for the current agent if it doesn't exist
    if st.session_state.current_agent not in st.session_state.chat_history:
        st.session_state.chat_history[st.session_state.current_agent] = []
    
    # Get chat history for the current agent
    agent_chat_history = st.session_state.chat_history.get(st.session_state.current_agent, [])
    
    # Create a container for the chat messages
    chat_container = st.container()
    
    # Display chat messages
    with chat_container:
        chat.display_chat_messages(agent_chat_history)
        
        # If waiting for a response, show a spinner
        if st.session_state.waiting_for_response:
            with st.chat_message("assistant"):
                st.write("Thinking...")
    
    # Debug info for admin users
    if st.session_state.debug_mode and st.session_state.role == "admin":
        with st.expander("Debug Information", expanded=False):
            st.subheader("Session Information")
            st.write(f"Username: {st.session_state.username}")
            st.write(f"Role: {st.session_state.role}")
            st.write(f"Current Agent: {st.session_state.current_agent}")
            
            st.subheader("Chat History")
            st.write(f"Messages in current chat: {len(agent_chat_history)}")
            
            # Display raw chat history
            st.json(agent_chat_history)
    
    # Check if there's a new message in the session state
    if st.session_state.new_message is not None:
        # Process the message
        debug_info = process_message(st.session_state.new_message, agent_chat_history)
        
        # Clear the new message
        st.session_state.new_message = None
        
        # Show agent recommendations if available
        if debug_info and st.session_state.show_agent_recommendation:
            current_agent = st.session_state.current_agent
            # Filter out the current agent
            other_recommendations = [a for a in debug_info if a != current_agent]
            if other_recommendations:
                st.info(f"💡 This query might also be suitable for: {', '.join(other_recommendations)}")
        
        # Force a rerun to update the UI
        st.rerun()
    
    # Chat input
    user_input = st.chat_input("Type your message here...")
    
    if user_input:
        # Store the message in session state to be processed after rerun
        st.session_state.new_message = user_input
        st.rerun()

if __name__ == "__main__":
    main()