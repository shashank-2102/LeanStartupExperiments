"""
Admin module for multi-agent chatbot system
Allows admin users to manage agents, users, and system configuration
"""
import streamlit as st
import pandas as pd
import db_manager
import rag_system
import csv_helper  # Add import for CSV helper functions
import io  # For buffer operations with CSV data
import datetime  # For formatting timestamps
import traceback  # For error tracking

def show_admin_page():
    """Display the admin page with tabs for different admin functions"""
    st.title("Admin Dashboard")
    
    # Check if user is admin
    if not st.session_state.authenticated or st.session_state.role != "admin":
        st.error("You do not have permission to access this page.")
        return
    
    # Create tabs for different admin functions
    tab1, tab2, tab3, tab4 = st.tabs(["Manage Agents", "Manage Users", "Chat History", "System Config"])
    
    with tab1:
        manage_agents()
    
    with tab2:
        manage_users()
    
    with tab3:
        manage_chat_history()
    
    with tab4:
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
            elif len(reset_password) < 1:
                st.error("Password must be at least 1 characters long.")
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
    
    # Add CSV import/export section
    st.subheader("CSV Import/Export")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Import users from CSV")
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv", help="CSV must have 'username' and 'password' columns. 'role' column is optional.")
        
        if uploaded_file is not None:
            if st.button("Import Users"):
                import csv_helper
                success_count, error_count, error_messages = csv_helper.import_users_from_csv(uploaded_file)
                
                if success_count > 0:
                    st.success(f"Successfully imported {success_count} users.")
                
                if error_count > 0:
                    with st.expander(f"Errors ({error_count})", expanded=True):
                        for error in error_messages:
                            st.error(error)
                
                if success_count > 0:
                    # Force refresh to show new users
                    st.rerun()
    
    with col2:
        st.write("Export users to CSV")
        if st.button("Export Users"):
            import csv_helper
            csv_data = csv_helper.export_users_to_csv()
            
            if csv_data:
                # Offer download link
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name="users.csv",
                    mime="text/csv",
                )
            else:
                st.error("No users to export.")

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

def manage_chat_history():
    """Admin function to view and export chat history"""
    st.header("Chat History Management")
    
    # Get a sample of recent chat history for display
    try:
        # First try the direct SQL approach
        try:
            # Get database session
            from models import Session
            session = Session()
            
            try:
                # Query to get recent conversations with limited data
                from sqlalchemy import text
                
                query = text("""
                SELECT 
                    u.username as user_username,
                    a.name as agent_name,
                    ch.conversation_id,
                    ch.created_at,
                    CASE 
                        WHEN ch.messages IS NULL THEN 0
                        WHEN ch.messages = '[]' THEN 0
                        WHEN jsonb_typeof(ch.messages) = 'array' THEN jsonb_array_length(ch.messages)
                        ELSE 0
                    END as message_count
                FROM 
                    chat_history ch
                    JOIN users u ON ch.user_id = u.id
                    JOIN agents a ON ch.agent_id = a.id
                ORDER BY
                    ch.created_at DESC
                LIMIT 50
                """)
                
                result = session.execute(query)
                
                # Create data for display
                chat_data = []
                for row in result:
                    # Format created_at
                    created_at = row.created_at
                    if created_at:
                        formatted_date = created_at.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        formatted_date = "Unknown"
                    
                    # Add to chat data
                    chat_data.append({
                        "User": row.user_username,
                        "Agent": row.agent_name,
                        "Conversation ID": row.conversation_id[:8] + "...",  # Truncate for display
                        "Created At": formatted_date,
                        "Messages": row.message_count
                    })
                
                # Show data if available
                if chat_data:
                    st.subheader("Recent Conversations")
                    st.dataframe(chat_data, use_container_width=True)
                    return  # Exit the function if we successfully displayed data
                
            finally:
                session.close()
                
        except Exception as e:
            if st.session_state.debug_mode:
                st.warning(f"Direct SQL approach failed: {e}")
                st.code(traceback.format_exc())
            # Continue to fallback method
        
        # Fallback method: Use ORM approach
        try:
            from models import Session, ChatHistory, User, Agent
            session = Session()
            
            try:
                # Query using SQLAlchemy ORM
                chat_histories = (session.query(
                    ChatHistory, User.username, Agent.name
                )
                .join(User, ChatHistory.user_id == User.id)
                .join(Agent, ChatHistory.agent_id == Agent.id)
                .order_by(ChatHistory.created_at.desc())
                .limit(50)
                .all())
                
                # Process results
                chat_data = []
                for chat, username, agent_name in chat_histories:
                    # Format created_at
                    created_at = chat.created_at
                    if created_at:
                        formatted_date = created_at.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        formatted_date = "Unknown"
                    
                    # Count messages
                    messages = chat.messages if chat.messages else []
                    message_count = len(messages) if isinstance(messages, list) else 0
                    
                    # Add to chat data
                    chat_data.append({
                        "User": username,
                        "Agent": agent_name,
                        "Conversation ID": chat.conversation_id[:8] + "...",  # Truncate for display
                        "Created At": formatted_date,
                        "Messages": message_count
                    })
                
                # Show data if available
                if chat_data:
                    st.subheader("Recent Conversations")
                    st.dataframe(chat_data, use_container_width=True)
                else:
                    st.info("No chat history found.")
                
            finally:
                session.close()
                
        except Exception as e:
            if st.session_state.debug_mode:
                st.warning(f"ORM approach failed: {e}")
                st.code(traceback.format_exc())
            
            # Final fallback: Display a message
            st.info("No chat history found or unable to retrieve chat history.")
            
    except Exception as e:
        st.error(f"Error retrieving chat history: {e}")
        if st.session_state.debug_mode:
            st.code(traceback.format_exc())
    
    # Export section
    st.subheader("Export Chat History")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write("""
        Export the complete chat history to a CSV file. The export includes:
        - User information
        - Agent information
        - Conversation IDs
        - Timestamps
        - All messages with roles (user/assistant)
        
        Note: This operation might take some time if there are many conversations.
        """)
    
    with col2:
        if st.button("Export All Chat History", use_container_width=True):
            with st.spinner("Exporting chat history..."):
                csv_data = csv_helper.export_chat_history_to_csv()
                
                if csv_data:
                    # Generate filename with current timestamp
                    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"chat_history_export_{now}.csv"
                    
                    # Offer download
                    st.download_button(
                        label="Download CSV File",
                        data=csv_data,
                        file_name=filename,
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                    st.success("Chat history exported successfully!")
                else:
                    st.error("No chat history to export or an error occurred.")