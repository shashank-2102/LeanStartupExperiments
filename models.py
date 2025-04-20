from sqlalchemy import Column, String, Integer, Text, ForeignKey, create_engine, MetaData, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os
import json
import pickle
import base64

# Create a base class for declarative models
Base = declarative_base()

# Define ORM models
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(String(20), default='user')
    
    # One-to-many relationship with ChatHistory
    chats = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")

class Agent(Base):
    __tablename__ = 'agents'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    system_prompt = Column(Text, nullable=False)
    
    # One-to-many relationship with ChatHistory
    chats = relationship("ChatHistory", back_populates="agent", cascade="all, delete-orphan")

class ChatHistory(Base):
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=False)
    messages = Column(JSON, default=list)
    
    # Many-to-one relationships
    user = relationship("User", back_populates="chats")
    agent = relationship("Agent", back_populates="chats")

class Config(Base):
    __tablename__ = 'config'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text)

# Database connection and session management
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    db_url = 'sqlite:///multi_agent_chatbot.db'

# If db_url starts with postgresql but you're having issues, use SQLite instead
if db_url and db_url.startswith('postgresql'):
    print("Using SQLite instead of PostgreSQL due to connection issues")
    db_url = 'sqlite:///multi_agent_chatbot.db'

# Create engine with appropriate parameters based on database type
if db_url.startswith('sqlite'):
    # SQLite specific configuration
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},  # Allows multiple threads to access SQLite
        pool_pre_ping=True,
        pool_recycle=300
    )
else:
    # PostgreSQL or other database configuration
    engine = create_engine(
        db_url,
        pool_pre_ping=True,  # Check connection before use
        pool_recycle=300,    # Recycle connections every 5 minutes
        pool_timeout=30,     # Connection timeout 
        max_overflow=10,     # Allow up to 10 connections beyond pool_size
        pool_size=5,         # Maintain a pool of 5 connections
        connect_args={
            "connect_timeout": 10,  # Connection timeout in seconds
            "application_name": "Multi-Agent-Chatbot" # Identify application in database logs
        }
    )

Session = sessionmaker(bind=engine)

def setup_database():
    """Initialize the database with tables and default data"""
    # Initialize session variable
    session = None
    
    # Create all tables - use try/except to handle connection issues
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(engine, checkfirst=True)
    except Exception as e:
        print(f"Error setting up database tables: {e}")
        return
        
    # Continue with rest of setup
    
    # Create session and add initial data with error handling
    try:
        # Create a new session
        session = Session()
        
        # Check if admin user exists
        admin_user = session.query(User).filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                password='JADS1234',
                role='admin'
            )
            session.add(admin_user)
        
        # Check if default agents exist
        if session.query(Agent).count() == 0:
            default_agents = [
                Agent(
                    name="General Assistant",
                    description="A helpful, balanced, and honest assistant that can discuss a wide range of topics.",
                    system_prompt="You are a helpful, balanced, and honest assistant. You answer questions thoughtfully, acknowledging different perspectives on complex issues. You never claim to have personal opinions, feelings, or experiences. If a question is ambiguous, harmful, or you don't know the answer, say so clearly."
                ),
                Agent(
                    name="Code Expert",
                    description="A specialized assistant that helps with programming and coding questions.",
                    system_prompt="You are a coding expert assistant. Provide clear, efficient, and well-commented code examples. Explain your approach and consider edge cases. If multiple languages or solutions are appropriate, note the tradeoffs. Format code with proper syntax highlighting using triple backticks. Avoid deprecated features and insecure patterns."
                ),
                Agent(
                    name="Creative Writer",
                    description="An assistant focused on creative writing, storytelling, and creative content generation.",
                    system_prompt="You are a creative writing assistant with a flair for engaging, imaginative content. Help users craft compelling stories, develop characters, refine plots, and generate creative ideas. Provide constructive feedback on writing while maintaining the user's voice and intent. When asked to generate content, create vivid, original material that matches the requested style and tone."
                )
            ]
            for agent in default_agents:
                session.add(agent)
        
        # Check if config exists (for OpenAI API key)
        config = session.query(Config).filter_by(key='openai_api_key').first()
        if not config:
            config = Config(key='openai_api_key', value='')
            session.add(config)
        
        # Commit all changes
        session.commit()
    except Exception as e:
        print(f"Error initializing database data: {e}")
        if session:
            session.rollback()
    finally:
        # Close session
        if session:
            session.close()

def encode_pickle(obj):
    """Convert a Python object to a base64 encoded string"""
    pickled = pickle.dumps(obj)
    return base64.b64encode(pickled).decode('utf-8')

def decode_pickle(encoded_str):
    """Convert a base64 encoded string back to a Python object"""
    if not encoded_str:
        return None
    try:
        return pickle.loads(base64.b64decode(encoded_str.encode('utf-8')))
    except:
        return None