"""
Agent module for multi-agent chatbot system
Handles communication with the OpenAI API
"""
import os
from openai import OpenAI
import db_manager

# Initialize OpenAI client
def get_openai_client():
    """Get OpenAI client with the API key from config"""
    # Get API key from database config or environment variable
    config = db_manager.get_config()
    api_key = config.get("openai_api_key", "")
    
    # If not found in database, try environment variable
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    
    # Return OpenAI client
    return OpenAI(api_key=api_key)

def get_agent_response(user_input, system_prompt, chat_history):
    """
    Get a response from the agent using the OpenAI API
    
    Args:
        user_input (str): The user's input message
        system_prompt (str): The system prompt for the agent
        chat_history (list): The chat history
        
    Returns:
        str: The agent's response
    """
    if not system_prompt:
        system_prompt = "You are a helpful assistant."
    
    # Check if OpenAI API key is available
    config = db_manager.get_config()
    api_key = config.get("openai_api_key", "")
    
    if not api_key and not os.environ.get("OPENAI_API_KEY"):
        return "No OpenAI API key is configured. Click the 'Configure OpenAI API Key' button in the sidebar to set up your API key."
    
    # Initialize OpenAI client
    try:
        client = get_openai_client()
        
        # Create messages for API
        messages = []
        
        # Add system prompt
        messages.append({"role": "system", "content": system_prompt})
        
        # Add chat history (except the last user message which we'll add separately)
        if chat_history:
            # Only include the most recent 10 messages to keep within token limits
            recent_messages = chat_history[-10:-1] if len(chat_history) > 10 else chat_history[:-1]
            for msg in recent_messages:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add user input
        messages.append({"role": "user", "content": user_input})
        
        # Get response from OpenAI API
        # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=800,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        
        # Return the response content
        return response.choices[0].message.content
    except Exception as e:
        # Handle API errors
        print(f"Error calling OpenAI API: {str(e)}")
        
        # Provide a more user-friendly error message
        if "auth" in str(e).lower() or "api key" in str(e).lower():
            return "Authentication error: The OpenAI API key may be invalid. Click the 'Configure OpenAI API Key' button in the sidebar to update your API key."
        elif "timeout" in str(e).lower() or "connect" in str(e).lower():
            return "Connection error: Could not connect to OpenAI's servers. Please check your internet connection and try again."
        else:
            return f"I'm sorry, I encountered an error when trying to respond: {str(e)}. Please try again later or contact support if the issue persists."
