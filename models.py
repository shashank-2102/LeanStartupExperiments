# Design the ORM model for the DB and connect to postgres via neon
# Makes default main agents that will be used in the langchain implementation

from sqlalchemy import Column, String, Integer, Text, ForeignKey, create_engine, MetaData, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os
import json
import time
from dotenv import load_dotenv
import datetime
import uuid

# Load environment variables from .env file
load_dotenv()

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
    conversation_id = Column(String(36), default=lambda: str(uuid.uuid4()))  # Default generates a UUID
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
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
def get_db_url():
    """Get database URL from environment variables for Neon.tech PostgreSQL"""
    # Check for Neon.tech specific environment variables
    db_user = os.environ.get('NEON_DB_USER')
    db_password = os.environ.get('NEON_DB_PASSWORD')
    db_host = os.environ.get('NEON_DB_HOST')
    db_name = os.environ.get('NEON_DB_NAME', 'neondb')
    
    # Construct PostgreSQL connection URL
    if db_user and db_password and db_host:
        return f'postgresql://{db_user}:{db_password}@{db_host}/{db_name}'
    
    # Fallback to DATABASE_URL if set
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        return db_url
    
    # If no database URL is found, raise an error
    raise ValueError("No PostgreSQL connection details found. Please set the NEON_DB_* environment variables.")

# Get the database URL
db_url = get_db_url()

# Configure PostgreSQL engine with appropriate settings for Neon.tech
engine = create_engine(
    db_url,
    pool_pre_ping=True,  # Check connection before use
    pool_recycle=300,    # Recycle connections every 5 minutes
    pool_timeout=30,     # Connection timeout
    max_overflow=5,      # Allow up to 5 connections beyond pool_size
    pool_size=3,         # Maintain a smaller pool for serverless environments
    echo=False,          # Set to True for debugging SQL queries
    connect_args={
        "connect_timeout": 10,  # Connection timeout in seconds
        "application_name": "Multi-Agent-Chatbot", # Identify application in database logs
        "sslmode": "require"    # Require SSL for Neon.tech connections
    }
)

Session = sessionmaker(bind=engine)

def setup_database():
    """Initialize the database with tables and default data"""
    # Initialize session variable
    session = None
    
    # Create all tables - use try/except to handle connection issues
    max_retries = 5
    retry_delay = 1  # Initial delay in seconds
    
    for attempt in range(max_retries):
        try:
            # Create tables if they don't exist
            Base.metadata.create_all(engine, checkfirst=True)
            print(f"Successfully created database tables on attempt {attempt+1}")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Error setting up database tables (attempt {attempt+1}/{max_retries}): {e}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed to set up database after {max_retries} attempts: {e}")
                raise  # Re-raise the exception after all retries have failed
    
    # Continue with rest of setup
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
            print("Created admin user")
        
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
            print("Created default agents")
        
        # Check if config exists (for OpenAI API key)
        config = session.query(Config).filter_by(key='openai_api_key').first()
        if not config:
            # Try to get from environment first
            openai_api_key = os.environ.get('OPENAI_API_KEY', '')
            config = Config(key='openai_api_key', value=openai_api_key)
            session.add(config)
            print("Initialized API key configuration")
        
        # Commit all changes
        session.commit()
        print("Database initialization successful")
    except Exception as e:
        print(f"Error initializing database data: {e}")
        if session:
            session.rollback()
    finally:
        # Close session
        if session:
            session.close()
