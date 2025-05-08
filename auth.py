import streamlit as st
import db_manager
import re

def show_auth_page():
    """Display the authentication page with login and registration tabs"""
    st.title("Multi-Agent Chatbot System")
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        show_login_form()
    
    with tab2:
        show_registration_form()

def show_login_form():
    """Display the login form"""
    st.header("Login")
    
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    
    if st.button("Login"):
        if not username or not password:
            st.error("Please enter both username and password")
            return
        
        # Verify credentials
        users = db_manager.get_users()
        user = next((u for u in users if u["username"] == username), None)
        
        if user and user["password"] == password:
            # Login successful
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.role = user["role"]
            
            # Set default agent if none selected
            agents = db_manager.get_agents()
            if agents and not st.session_state.current_agent:
                st.session_state.current_agent = agents[0]["name"]
                
            # Load chat history for the user
            load_user_chat_history(username)
            
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password")

def show_registration_form():
    """Display the registration form"""
    st.header("Register")
    
    new_username = st.text_input("Username", key="reg_username")
    new_password = st.text_input("Password", type="password", key="reg_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
    
    if st.button("Register"):
        # Validate inputs
        if not new_username or not new_password:
            st.error("Please provide both username and password")
            return
        
        if new_password != confirm_password:
            st.error("Passwords don't match")
            return
        
        if len(new_password) < 6:
            st.error("Password must be at least 6 characters long")
            return
        
        if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
            st.error("Username can only contain letters, numbers, and underscores")
            return
        
        # Check if username already exists
        users = db_manager.get_users()
        if any(u["username"] == new_username for u in users):
            st.error("Username already exists")
            return
        
        # Register the new user (normal user by default)
        new_user = {
            "username": new_username,
            "password": new_password,
            "role": "user"
        }
        
        # If this is the first user, make them an admin
        if not users:
            new_user["role"] = "admin"
        
        db_manager.add_user(new_user)
        
        st.success("Registration successful! You can now login.")

def logout():
    """Log out the current user"""
    # Reset session state
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.page = "chat"
    # Keep chat history in memory but don't show it

def load_user_chat_history(username):
    """Load chat history for the user"""
    chat_history = db_manager.load_chat_history(username)
    
    if chat_history:
        st.session_state.chat_history = chat_history
    else:
        st.session_state.chat_history = {}