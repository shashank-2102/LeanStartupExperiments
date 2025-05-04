"""
CSV Helper functions for the multi-agent chatbot system
Handles importing and exporting user data and chat history via CSV
"""
import pandas as pd
import io
import csv
import db_manager
import re

def import_users_from_csv(csv_file):
    """
    Import users from a CSV file and add them to the database
    
    Args:
        csv_file: StreamlitUploadedFile object containing the CSV data
        
    Returns:
        tuple: (success_count, error_count, error_messages)
    """
    try:
        # Read CSV file
        df = pd.read_csv(csv_file)
        
        # Validate column names
        required_columns = ['username', 'password']
        if not all(col in df.columns for col in required_columns):
            return 0, 0, ["CSV must contain 'username' and 'password' columns"]
        
        # Optional role column (default to 'user' if not present)
        if 'role' not in df.columns:
            df['role'] = 'user'
        
        # Process each row
        success_count = 0
        error_count = 0
        error_messages = []
        
        # Get existing users for duplicate checking
        existing_users = db_manager.get_users()
        existing_usernames = [user["username"] for user in existing_users]
        
        for _, row in df.iterrows():
            username = str(row['username']).strip()
            password = str(row['password']).strip()
            role = str(row['role']).strip().lower()
            
            # Validate username and password
            if not username or not password:
                error_count += 1
                error_messages.append(f"Skipped row: username and password cannot be empty")
                continue
                
            # Validate username format
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                error_count += 1
                error_messages.append(f"Skipped user '{username}': username can only contain letters, numbers, and underscores")
                continue
            
            # Check if username already exists
            if username in existing_usernames:
                error_count += 1
                error_messages.append(f"Skipped user '{username}': username already exists")
                continue
            
            # Validate password length
            if len(password) < 1:
                error_count += 1
                error_messages.append(f"Skipped user '{username}': password must be at least 1 characters long")
                continue
            
            # Validate role
            if role not in ['user', 'admin']:
                role = 'user'  # Default to user role if invalid
            
            # Add user to database
            user_data = {
                "username": username,
                "password": password,
                "role": role
            }
            
            if db_manager.add_user(user_data):
                success_count += 1
                # Add to existing_usernames to check future duplicates in the same file
                existing_usernames.append(username)
            else:
                error_count += 1
                error_messages.append(f"Failed to add user '{username}': database error")
        
        return success_count, error_count, error_messages
    
    except Exception as e:
        return 0, 1, [f"Error processing CSV file: {str(e)}"]

def export_users_to_csv():
    """
    Export all users from the database to a CSV file
    
    Returns:
        str: CSV data as a string
    """
    try:
        # Get all users from the database
        users = db_manager.get_users()
        
        if not users:
            return None
        
        # Create a DataFrame from the users list
        df = pd.DataFrame(users)
        
        # For security, replace actual passwords with placeholder
        df['password'] = '********'
        
        # Create CSV string
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        
        return csv_buffer.getvalue()
    
    except Exception as e:
        print(f"Error exporting users to CSV: {e}")
        return None

def export_chat_history_to_csv():
    """
    Export all chat history from the database to a CSV file
    
    Returns:
        str: CSV data as a string
    """
    try:
        # First, try the direct SQL approach
        try:
            # Get database session
            from models import Session
            session = Session()
            
            try:
                # Execute SQL query to join chat_history with users and agents tables
                from sqlalchemy import text
                
                query = text("""
                SELECT 
                    ch.id,
                    u.username as user_username,
                    a.name as agent_name,
                    ch.conversation_id,
                    ch.created_at,
                    ch.messages
                FROM 
                    chat_history ch
                    JOIN users u ON ch.user_id = u.id
                    JOIN agents a ON ch.agent_id = a.id
                ORDER BY
                    ch.created_at DESC
                """)
                
                # Execute the query
                result = session.execute(query)
                
                # Create a list of dictionaries for the result
                chat_records = []
                
                for row in result:
                    # Process the messages JSON
                    messages = row.messages if row.messages else []
                    
                    # If messages is a string (JSON), parse it
                    if isinstance(messages, str):
                        try:
                            import json
                            messages = json.loads(messages)
                        except:
                            messages = []
                    
                    # For each message in the conversation, create a record
                    if messages:
                        for i, msg in enumerate(messages):
                            # Extract message details
                            role = msg.get('role', 'unknown')
                            content = msg.get('content', '')
                            
                            # Format content for CSV (remove newlines)
                            content = content.replace('\n', ' ').replace('\r', '')
                            
                            # Create record
                            record = {
                                'chat_id': row.id,
                                'user_username': row.user_username,
                                'agent_name': row.agent_name,
                                'conversation_id': row.conversation_id,
                                'created_at': row.created_at,
                                'message_number': i + 1,
                                'role': role,
                                'content': content
                            }
                            
                            chat_records.append(record)
                    else:
                        # Empty conversation, create a single record
                        record = {
                            'chat_id': row.id,
                            'user_username': row.user_username,
                            'agent_name': row.agent_name,
                            'conversation_id': row.conversation_id,
                            'created_at': row.created_at,
                            'message_number': 0,
                            'role': 'system',
                            'content': 'Empty conversation'
                        }
                        
                        chat_records.append(record)
                
                # Create DataFrame
                if chat_records:
                    df = pd.DataFrame(chat_records)
                    
                    # Create CSV string
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False)
                    
                    return csv_buffer.getvalue()
            finally:
                session.close()
                
        except Exception as e:
            print(f"Direct SQL approach failed: {e}")
            import traceback
            print(traceback.format_exc())
            
            # Fall back to using db_manager approach
            print("Falling back to alternative method...")
            
        # Fallback method using db_manager functions
        # Get all users and agents first
        users = db_manager.get_users()
        agents = db_manager.get_agents()
        
        # Map user IDs to usernames and agent IDs to names
        user_map = {i+1: user["username"] for i, user in enumerate(users)}  # Assuming ID starts at 1
        agent_map = {i+1: agent["name"] for i, agent in enumerate(agents)}  # Assuming ID starts at 1
        
        # Use a direct database connection through models module
        from models import Session, ChatHistory
        session = Session()
        
        try:
            # Get all chat history entries
            chat_histories = session.query(ChatHistory).all()
            
            # Process each chat history entry
            chat_records = []
            
            for chat in chat_histories:
                user_id = chat.user_id
                agent_id = chat.agent_id
                username = user_map.get(user_id, f"unknown_user_{user_id}")
                agent_name = agent_map.get(agent_id, f"unknown_agent_{agent_id}")
                
                # Process messages
                messages = chat.messages if chat.messages else []
                
                # For each message in the conversation, create a record
                if messages:
                    for i, msg in enumerate(messages):
                        # Extract message details
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        
                        # Format content for CSV (remove newlines)
                        content = content.replace('\n', ' ').replace('\r', '')
                        
                        # Create record
                        record = {
                            'chat_id': chat.id,
                            'user_username': username,
                            'agent_name': agent_name,
                            'conversation_id': chat.conversation_id,
                            'created_at': chat.created_at,
                            'message_number': i + 1,
                            'role': role,
                            'content': content
                        }
                        
                        chat_records.append(record)
                else:
                    # Empty conversation, create a single record
                    record = {
                        'chat_id': chat.id,
                        'user_username': username,
                        'agent_name': agent_name,
                        'conversation_id': chat.conversation_id,
                        'created_at': chat.created_at,
                        'message_number': 0,
                        'role': 'system',
                        'content': 'Empty conversation'
                    }
                    
                    chat_records.append(record)
            
            # Create DataFrame
            if chat_records:
                df = pd.DataFrame(chat_records)
                
                # Create CSV string
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                
                return csv_buffer.getvalue()
        finally:
            session.close()
            
        return None  # No chat records found
    
    except Exception as e:
        print(f"Error exporting chat history to CSV: {e}")
        import traceback
        print(traceback.format_exc())
        return None