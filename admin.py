"""
Admin module for multi-agent chatbot system
Allows admin users to manage agents, users, and system configuration
"""
import streamlit as st
import pandas as pd
import db_manager
import rag_system

def show_admin_page():
    """Display the admin page with tabs for different admin functions"""
    st.title("Admin Dashboard")
    
    # Check if user is admin
    if not st.session_state.authenticated or st.session_state.role != "admin":
        st.error("You do not have permission to access this page.")
        return
    
    # Create tabs for different admin functions
    tab1, tab2, tab3 = st.tabs(["Manage Agents", "Manage Users", "System Config"])
    
    with tab1:
        manage_agents()
    
    with tab2:
        manage_users()
    
    with tab3:
        system_config()

def manage_agents():
    """Admin function to manage agents"""
    st.header("Manage Agents")
    
    # Get current agents
    agents = db_manager.get_agents()
    
    # Convert to DataFrame for display
    if agents:
        agent_df = pd.DataFrame(agents)
        
        # Display agents in a dataframe with editable cells
        edited_df = st.data_editor(
            agent_df,
            column_config={
                "name": st.column_config.TextColumn("Agent Name", width="medium"),
                "description": st.column_config.TextColumn("Description", width="large"),
                "system_prompt": st.column_config.TextColumn("System Prompt", width="large"),
            },
            use_container_width=True,
            num_rows="dynamic",
            key="agent_editor"
        )
        
        # Save changes button
        if st.button("Save Changes to Agents"):
            try:
                # Find deleted rows (in original but not in edited)
                original_names = set(agent_df["name"])
                edited_names = set(edited_df["name"])
                
                # Handle modified rows
                for i, row in edited_df.iterrows():
                    agent_data = row.to_dict()
                    
                    # Check if this is an edited existing agent
                    if i < len(agents) and agent_data["name"] in original_names:
                        db_manager.update_agent(i, agent_data)
                    # Check if this is a new agent
                    elif agent_data["name"] not in original_names:
                        db_manager.add_agent(agent_data)
                
                # Update RAG system with new agents
                rag_system.update_agent_knowledge()
                
                st.success("Agents updated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating agents: {e}")
    else:
        st.warning("No agents found in the database. Add your first agent below.")
    
    # Add new agent section
    st.subheader("Add New Agent")
    
    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input("Agent Name")
    with col2:
        new_description = st.text_input("Description")
    
    new_system_prompt = st.text_area("System Prompt", height=150)
    
    if st.button("Add Agent"):
        if not new_name or not new_system_prompt:
            st.error("Please provide at least a name and system prompt.")
        else:
            try:
                new_agent = {
                    "name": new_name,
                    "description": new_description,
                    "system_prompt": new_system_prompt
                }
                
                db_manager.add_agent(new_agent)
                
                # Update RAG system with new agent
                rag_system.update_agent_knowledge()
                
                st.success(f"Agent '{new_name}' added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding agent: {e}")

def manage_users():
    """Admin function to manage users"""
    st.header("Manage Users")
    
    # Get current users
    users = db_manager.get_users()
    
    # Convert to DataFrame for display
    if users:
        # Create dataframe but hide passwords in the display
        user_df = pd.DataFrame(users)
        
        # Replace actual passwords with placeholder for display
        display_df = user_df.copy()
        display_df["password"] = "********"
        
        # Display users in a dataframe with editable cells
        edited_df = st.data_editor(
            display_df,
            column_config={
                "username": st.column_config.TextColumn("Username", width="medium"),
                "password": st.column_config.TextColumn("Password", width="medium"),
                "role": st.column_config.SelectboxColumn(
                    "Role", 
                    options=["user", "admin"],
                    width="small"
                ),
            },
            disabled=["password"],
            use_container_width=True,
            key="user_editor"
        )
        
        # Save changes button
        if st.button("Save Changes to Users"):
            try:
                # Since we can't edit passwords in the table, we need to merge changes
                # with original passwords
                for i, row in edited_df.iterrows():
                    if i < len(user_df):
                        # Update role for existing users
                        user_df.at[i, "role"] = row["role"]
                
                # Update users in database
                db_manager.update_users(user_df)
                
                st.success("Users updated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating users: {e}")
    else:
        st.warning("No users found in the database.")
    
    # Reset password section
    st.subheader("Reset User Password")
    
    if users:
        usernames = [user["username"] for user in users]
        reset_username = st.selectbox("Select User", usernames)
        reset_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        if st.button("Reset Password"):
            if reset_password != confirm_password:
                st.error("Passwords don't match.")
            elif len(reset_password) < 6:
                st.error("Password must be at least 6 characters long.")
            else:
                try:
                    # Find the user and update password
                    user_df = pd.DataFrame(users)
                    user_idx = user_df[user_df["username"] == reset_username].index[0]
                    user_df.at[user_idx, "password"] = reset_password
                    
                    # Update users in database
                    db_manager.update_users(user_df)
                    
                    st.success(f"Password reset successfully for {reset_username}!")
                except Exception as e:
                    st.error(f"Error resetting password: {e}")

def system_config():
    """Admin function to configure system settings"""
    st.header("System Configuration")
    
    # Get current configuration
    config = db_manager.get_config()
    
    # OpenAI API key configuration
    st.subheader("OpenAI API Configuration")
    
    current_api_key = config.get("openai_api_key", "")
    api_key_placeholder = "****************************" if current_api_key else "No API key set"
    
    # Show masked API key and option to update
    st.text_input("Current OpenAI API Key", value=api_key_placeholder, disabled=True)
    new_api_key = st.text_input("New OpenAI API Key (leave blank to keep current)", type="password")
    
    if st.button("Update API Key"):
        if new_api_key:
            try:
                # Update config in database
                config["openai_api_key"] = new_api_key
                db_manager.update_config(config)
                
                st.success("API key updated successfully!")
            except Exception as e:
                st.error(f"Error updating API key: {e}")
    
    # Database connection information (read-only)
    st.subheader("Database Information")
    st.info("Database connection is configured via environment variables. If you need to change the database connection, update the environment variables and restart the application.")
