from models import User, Agent, ChatHistory, Config, Session
import os
import json
import time
from sqlalchemy.exc import SQLAlchemyError, OperationalError

def setup_database():
    """Initialize the database with tables and default data"""
    # Import here to avoid circular import
    from models import setup_database
    
    tries = 0
    max_tries = 5
    retry_delay = 2  # seconds
    
    # Try multiple times to connect to the database
    while tries < max_tries:
        try:
            setup_database()
            # If successful, break out of the loop
            print("Database setup completed successfully")
            return
        except Exception as e:
            tries += 1
            print(f"Error setting up database (attempt {tries}/{max_tries}): {e}")
            if tries < max_tries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                # Increase delay for next attempt (exponential backoff)
                retry_delay *= 2
            else:
                print("Maximum retry attempts reached. Database setup failed.")
                # Raise the exception to make sure the application knows there was a failure
                raise

def execute_with_retry(func, *args, **kwargs):
    """Execute a database function with retry logic for handling connection issues"""
    max_tries = 5
    retry_delay = 1  # seconds
    
    for attempt in range(max_tries):
        try:
            return func(*args, **kwargs)
        except (OperationalError, SQLAlchemyError) as e:
            # Check if this is a connection error that we can retry
            if attempt < max_tries - 1:
                print(f"Database operation failed (attempt {attempt+1}/{max_tries}): {e}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed after {max_tries} attempts: {e}")
                raise  # Re-raise the last exception

# User management functions
def get_users():
    """Get list of users"""
    def _get_users():
        session = Session()
        try:
            users = session.query(User).all()
            # Convert to list of dictionaries for compatibility with existing code
            return [{"username": user.username, "password": user.password, "role": user.role} for user in users]
        finally:
            session.close()
    
    try:
        return execute_with_retry(_get_users)
    except Exception as e:
        print(f"Failed to get users: {e}")
        return []  # Return empty list if all attempts fail

def add_user(user_data):
    """Add a new user"""
    def _add_user(user_data):
        session = Session()
        try:
            # Check if user already exists
            existing_user = session.query(User).filter_by(username=user_data["username"]).first()
            if existing_user:
                return False
                
            # Create new user
            new_user = User(
                username=user_data["username"],
                password=user_data["password"],
                role=user_data["role"]
            )
            session.add(new_user)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    try:
        return execute_with_retry(_add_user, user_data)
    except Exception as e:
        print(f"Failed to add user: {e}")
        return False

def update_users(users_list):
    """Update users from list of dictionaries"""
    def _update_users(users_list):
        session = Session()
        try:
            # Get all current users
            current_users = {user.username: user for user in session.query(User).all()}
            
            # Update existing users
            for user_data in users_list:
                if user_data["username"] in current_users:
                    user = current_users[user_data["username"]]
                    user.password = user_data["password"]
                    user.role = user_data["role"]
            
            # Commit changes
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    try:
        return execute_with_retry(_update_users, users_list)
    except Exception as e:
        print(f"Failed to update users: {e}")
        return False

# Agent management functions
def get_agents():
    """Get list of agents"""
    def _get_agents():
        session = Session()
        try:
            agents = session.query(Agent).all()
            # Convert to list of dictionaries for compatibility with existing code
            return [{"name": agent.name, "description": agent.description, "system_prompt": agent.system_prompt} for agent in agents]
        finally:
            session.close()
    
    try:
        return execute_with_retry(_get_agents)
    except Exception as e:
        print(f"Failed to get agents: {e}")
        # Return at least one default agent if database fails
        return [{
            "name": "General Assistant",
            "description": "A helpful assistant that can discuss a wide range of topics.",
            "system_prompt": "You are a helpful assistant. Answer questions clearly and honestly."
        }]

def update_agent(index, agent_data):
    """Update an existing agent"""
    def _update_agent(index, agent_data):
        session = Session()
        try:
            # Get all agents (ordered by ID)
            agents = session.query(Agent).order_by(Agent.id).all()
            
            # Check if index is valid
            if 0 <= index < len(agents):
                agent = agents[index]
                
                # Update agent data
                agent.name = agent_data["name"]
                agent.description = agent_data["description"]
                agent.system_prompt = agent_data["system_prompt"]
                
                # Commit changes
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    try:
        return execute_with_retry(_update_agent, index, agent_data)
    except Exception as e:
        print(f"Failed to update agent: {e}")
        return False

def add_agent(agent_data):
    """Add a new agent"""
    def _add_agent(agent_data):
        session = Session()
        try:
            # Create new agent
            new_agent = Agent(
                name=agent_data["name"],
                description=agent_data["description"],
                system_prompt=agent_data["system_prompt"]
            )
            session.add(new_agent)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    try:
        return execute_with_retry(_add_agent, agent_data)
    except Exception as e:
        print(f"Failed to add agent: {e}")
        return False

# Chat history functions
def save_chat_history(username, agent_name, conversation_id, chat_history):
    """Save chat history for a user, agent, and specific conversation"""
    # def _save_chat_history(username, agent_name, conversation_id, chat_history):
    session = Session()
    try:
        # Get user and agent
        user = session.query(User).filter_by(username=username).first()
        agent = session.query(Agent).filter_by(name=agent_name).first()
        
        if not user or not agent:
            print(f"User {username} or Agent {agent_name} not found in database")
            return False
        
        # Make sure chat_history is JSON serializable
        try:
            json.dumps(chat_history)
        except (TypeError, OverflowError) as e:
            print(f"Error serializing chat history: {e}")
            safe_chat_history = []
            for msg in chat_history:
                safe_msg = {
                    "role": str(msg.get("role", "")),
                    "content": str(msg.get("content", ""))
                }
                safe_chat_history.append(safe_msg)
            chat_history = safe_chat_history
        
        # Check if chat history for this conversation already exists
        existing_chat = session.query(ChatHistory).filter_by(
            user_id=user.id, agent_id=agent.id, conversation_id=conversation_id
        ).first()
        
        if existing_chat:
            # Update existing chat history
            existing_chat.messages = chat_history
        else:
            # Create new chat history entry
            new_chat = ChatHistory(
                user_id=user.id,
                agent_id=agent.id,
                conversation_id=conversation_id,
                messages=chat_history
            )
            session.add(new_chat)
        
        # Commit changes
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error in save_chat_history: {e}")
        raise e
    finally:
        session.close()
    
    try:
        return execute_with_retry(_save_chat_history, username, agent_name, conversation_id, chat_history)
    except Exception as e:
        print(f"Failed to save chat history after retries: {e}")
        return False

# def load_chat_history(username):
#     """Load chat history for a user"""
#     def _load_chat_history(username):
#         session = Session()
#         try:
#             # Get user
#             user = session.query(User).filter_by(username=username).first()
#             if not user:
#                 print(f"User {username} not found when loading chat history")
#                 return {}
            
#             # Get all chat histories for this user
#             chat_histories = session.query(ChatHistory, Agent).join(Agent).filter(
#                 ChatHistory.user_id == user.id
#             ).order_by(ChatHistory.created_at.desc()).all()
            
#             # Convert to nested dictionary: agent_name -> conversation_id -> messages
#             result = {}
#             for chat, agent in chat_histories:
#                 if agent.name not in result:
#                     result[agent.name] = {}
                
#                 result[agent.name][chat.conversation_id] = {
#                     'messages': chat.messages,
#                     'created_at': chat.created_at.isoformat() if chat.created_at else None
#                 }
            
#             return result
#         finally:
#             session.close()
    
#     try:
#         return execute_with_retry(_load_chat_history, username)
#     except Exception as e:
#         print(f"Failed to load chat history: {e}")
#         return {}

def get_conversations(username, agent_name):
    """Get list of conversations for a user and agent"""
    def _get_conversations(username, agent_name):
        session = Session()
        try:
            # Get user and agent
            user = session.query(User).filter_by(username=username).first()
            agent = session.query(Agent).filter_by(name=agent_name).first()
            
            if not user or not agent:
                return []
            
            # Try to get conversations with conversation_id field
            try:
                # Get all conversations for this user and agent
                conversations = session.query(ChatHistory).filter_by(
                    user_id=user.id, agent_id=agent.id
                ).all()
                
                # Convert to list of dicts with conversation_id and created_at
                return [{
                    'conversation_id': getattr(conv, 'conversation_id', 'default'),
                    'created_at': getattr(conv, 'created_at', None).isoformat() if getattr(conv, 'created_at', None) else None,
                    'message_count': len(conv.messages) if hasattr(conv, 'messages') and conv.messages else 0
                } for conv in conversations]
            except Exception as e:
                print(f"Error fetching conversations with new schema: {e}")
                # Fallback for older database schema
                return [{
                    'conversation_id': 'default',
                    'created_at': None,
                    'message_count': 0
                }]
        finally:
            session.close()
    
    try:
        return execute_with_retry(_get_conversations, username, agent_name)
    except Exception as e:
        print(f"Failed to get conversations: {e}")
        return []

def load_chat_history(username):
    """Load chat history for a user"""
    def _load_chat_history(username):
        session = Session()
        try:
            # Get user
            user = session.query(User).filter_by(username=username).first()
            if not user:
                print(f"User {username} not found when loading chat history")
                return {}
            
            # Get all chat histories for this user
            chat_histories = session.query(ChatHistory, Agent).join(Agent).filter(
                ChatHistory.user_id == user.id
            ).all()
            
            # Convert to nested dictionary: agent_name -> conversation_id -> messages
            result = {}
            for chat, agent in chat_histories:
                if agent.name not in result:
                    result[agent.name] = {}
                
                # Get conversation ID, use a default if not present
                try:
                    # For databases with conversation_id column
                    conv_id = chat.conversation_id
                except AttributeError:
                    # For older database schemas without conversation_id
                    conv_id = "default"
                
                # Get created_at, use a default if not present
                try:
                    created_at = chat.created_at.isoformat() if chat.created_at else None
                except AttributeError:
                    created_at = None
                
                # Store messages with metadata
                result[agent.name][conv_id] = {
                    'messages': chat.messages,
                    'created_at': created_at
                }
            
            return result
        finally:
            session.close()
    
    try:
        return execute_with_retry(_load_chat_history, username)
    except Exception as e:
        print(f"Failed to load chat history: {e}")
        return {}  # Return empty dict if all attempts fail

# Config functions
def get_config():
    """Get the application configuration"""
    def _get_config():
        session = Session()
        try:
            configs = session.query(Config).all()
            
            # Convert to dictionary
            config_dict = {}
            for config in configs:
                config_dict[config.key] = config.value
            
            return config_dict
        finally:
            session.close()
    
    try:
        return execute_with_retry(_get_config)
    except Exception as e:
        print(f"Failed to get config: {e}")
        return {"openai_api_key": ""}  # Return empty config as fallback

def update_config(config_dict):
    """Update the application configuration"""
    def _update_config(config_dict):
        session = Session()
        try:
            for key, value in config_dict.items():
                # Check if config exists
                config = session.query(Config).filter_by(key=key).first()
                
                if config:
                    # Update existing config
                    config.value = value
                else:
                    # Create new config
                    new_config = Config(key=key, value=value)
                    session.add(new_config)
            
            # Commit changes
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    try:
        return execute_with_retry(_update_config, config_dict)
    except Exception as e:
        print(f"Failed to update config: {e}")
        return False