"""
Script to run when database changes made. Alternatively, run models.py to create the database and tables.
This preserves existing data while updating the schema.
"""
import os
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

def get_db_url():
    """Get database URL from environment variables"""
    db_user = os.environ.get('NEON_DB_USER')
    db_password = os.environ.get('NEON_DB_PASSWORD')
    db_host = os.environ.get('NEON_DB_HOST')
    db_name = os.environ.get('NEON_DB_NAME', 'neondb')
    
    if not all([db_user, db_password, db_host]):
        raise ValueError("Missing database credentials. Please check your .env file.")
    
    return f'postgresql://{db_user}:{db_password}@{db_host}/{db_name}?sslmode=require'

def update_schema():
    """Add missing columns to the chat_history table"""
    try:
        # Connect to database
        db_url = get_db_url()
        engine = create_engine(db_url, connect_args={"sslmode": "require"})
        
        with engine.connect() as connection:
            # Check if conversation_id column exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'chat_history' 
                AND column_name = 'conversation_id'
            """))
            
            has_conversation_id = bool(result.fetchone())
            
            if not has_conversation_id:
                print("Adding conversation_id column to chat_history table...")
                connection.execute(text("""
                    ALTER TABLE chat_history 
                    ADD COLUMN conversation_id VARCHAR(36) DEFAULT NULL
                """))
                
                # Generate default UUIDs for existing rows
                print("Updating existing rows with default UUIDs...")
                result = connection.execute(text("SELECT id FROM chat_history"))
                row_ids = [row[0] for row in result]
                
                for row_id in row_ids:
                    new_uuid = str(uuid.uuid4())
                    connection.execute(
                        text("UPDATE chat_history SET conversation_id = :uuid WHERE id = :id"),
                        {"uuid": new_uuid, "id": row_id}
                    )
                
                print(f"Updated {len(row_ids)} existing rows with unique conversation IDs")
            else:
                print("conversation_id column already exists in chat_history table.")
            
            # Check if created_at column exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'chat_history' 
                AND column_name = 'created_at'
            """))
            
            has_created_at = bool(result.fetchone())
            
            if not has_created_at:
                print("Adding created_at column to chat_history table...")
                connection.execute(text("""
                    ALTER TABLE chat_history 
                    ADD COLUMN created_at TIMESTAMP DEFAULT NOW()
                """))
                print("Added created_at column with current timestamp")
            else:
                print("created_at column already exists in chat_history table.")
            
            connection.commit()
            
        print("\n✅ Database schema updated successfully.")
        print("\nYou can now run your application with 'streamlit run app.py'")
        
    except Exception as e:
        print(f"❌ Error updating database schema: {e}")
        raise

if __name__ == "__main__":
    update_schema()