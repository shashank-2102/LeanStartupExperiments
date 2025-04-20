from models import User, Agent, ChatHistory, Config, Session
import os
import json
import time

def setup_database():
    """Initialize the database with tables and default data"""
    # Import here to avoid circular import
    from models import setup_database
    
    tries = 0
    max_tries = 3
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

# User management functions
def get_users():
    """Get list of users"""
    session = Session()
    max_tries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_tries):
        try:
            users = session.query(User).all()
            # Convert to list of dictionaries for compatibility with existing code
            return [{"username": user.username, "password": user.password, "role": user.role} for user in users]
        except Exception as e:
            if attempt < max_tries - 1:  # Don't sleep on the last attempt
                print(f"Error getting users (attempt {attempt+1}/{max_tries}): {e}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed to get users after {max_tries} attempts: {e}")
                return []  # Return empty list if all attempts fail
        finally:
            session.close()

def add_user(user_data):
    """Add a new user"""
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
    finally:
        session.close()

def update_users(users_list):
    """Update users from list of dictionaries"""
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
    finally:
        session.close()

# Agent management functions
def get_agents():
    """Get list of agents"""
    session = Session()
    max_tries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_tries):
        try:
            agents = session.query(Agent).all()
            # Convert to list of dictionaries for compatibility with existing code
            return [{"name": agent.name, "description": agent.description, "system_prompt": agent.system_prompt} for agent in agents]
        except Exception as e:
            if attempt < max_tries - 1:  # Don't sleep on the last attempt
                print(f"Error getting agents (attempt {attempt+1}/{max_tries}): {e}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed to get agents after {max_tries} attempts: {e}")
                # Return at least one default agent if database fails
                return [{
                    "name": "General Assistant",
                    "description": "A helpful assistant that can discuss a wide range of topics.",
                    "system_prompt": "You are a helpful assistant. Answer questions clearly and honestly."
                }]
        finally:
            session.close()

def update_agent(index, agent_data):
    """Update an existing agent"""
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
    finally:
        session.close()

def add_agent(agent_data):
    """Add a new agent"""
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
    finally:
        session.close()

# Chat history functions
def save_chat_history(username, agent_name, chat_history):
    """Save chat history for a user and agent"""
    session = Session()
    try:
        # Get user and agent
        user = session.query(User).filter_by(username=username).first()
        agent = session.query(Agent).filter_by(name=agent_name).first()
        
        if not user or not agent:
            return False
        
        # Check if chat history already exists
        existing_chat = session.query(ChatHistory).filter_by(
            user_id=user.id, agent_id=agent.id
        ).first()
        
        if existing_chat:
            # Update existing chat history
            existing_chat.messages = chat_history
        else:
            # Create new chat history
            new_chat = ChatHistory(
                user_id=user.id,
                agent_id=agent.id,
                messages=chat_history
            )
            session.add(new_chat)
        
        # Commit changes
        session.commit()
        return True
    finally:
        session.close()

def load_chat_history(username):
    """Load chat history for a user"""
    session = Session()
    max_tries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_tries):
        try:
            # Get user
            user = session.query(User).filter_by(username=username).first()
            if not user:
                return {}
            
            # Get all chat histories for this user
            chat_histories = session.query(ChatHistory, Agent).join(Agent).filter(
                ChatHistory.user_id == user.id
            ).all()
            
            # Convert to dictionary of agent_name: messages
            result = {}
            for chat, agent in chat_histories:
                result[agent.name] = chat.messages
            
            return result
        except Exception as e:
            if attempt < max_tries - 1:  # Don't sleep on the last attempt
                print(f"Error loading chat history (attempt {attempt+1}/{max_tries}): {e}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed to load chat history after {max_tries} attempts: {e}")
                return {}  # Return empty dict if all attempts fail
        finally:
            session.close()

# Config functions
def get_config():
    """Get the application configuration"""
    session = Session()
    max_tries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_tries):
        try:
            configs = session.query(Config).all()
            
            # Convert to dictionary
            config_dict = {}
            for config in configs:
                config_dict[config.key] = config.value
            
            return config_dict
        except Exception as e:
            if attempt < max_tries - 1:  # Don't sleep on the last attempt
                print(f"Error getting config (attempt {attempt+1}/{max_tries}): {e}")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed to get config after {max_tries} attempts: {e}")
                return {"openai_api_key": ""}  # Return empty config as fallback
        finally:
            session.close()

def update_config(config_dict):
    """Update the application configuration"""
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
    finally:
        session.close()