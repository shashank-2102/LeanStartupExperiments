"""
Agent module for multi-agent chatbot system
Handles communication with the OpenAI API and implements LangGraph structure
"""
import os
from openai import OpenAI
import db_manager
from dotenv import load_dotenv
from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END

# Load environment variables from .env file
load_dotenv()

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

def call_openai_api(client, messages, temperature=0.7, max_tokens=800):
    """
    Call the OpenAI API with the given messages
    
    Args:
        client: The OpenAI client
        messages: The messages to send to the API
        temperature: The temperature to use for generation
        max_tokens: The maximum number of tokens to generate
        
    Returns:
        str: The API response
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )
    
    return response.choices[0].message.content

def get_agent_response(user_input, system_prompt, chat_history):
    """
    Get a response from the agent using the OpenAI API with LangGraph structure
    
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
        
        # Define the LangGraph state as a simple dictionary
        state = {
            "user_input": user_input,
            "processed_input": "", # INPUT
            "primary_response": "", #SPECIALISED AGENT
            "final_response": "" # FORMATTING THE RESPONSE
        }
        
        # === Input Checker Agent ===
        def input_checker(state):
            """Process the user input to make it clearer for the model"""
            input_checker_prompt = """
            You are an input processing specialist. Your task is to:
            1. Analyze the user's input
            2. Rephrase it to be clearer and more specific
            3. Format it in a way that's optimized for AI processing
            4. Maintain all important details from the original query
            
            Your output should be well-structured and include all the key information from the original input.
            """
            
            # Create messages for input checker
            messages = []
            # Add context from chat history if available (last 3 messages for context)
            if chat_history:
                recent_context = chat_history[-3:] if len(chat_history) >= 3 else chat_history
                for msg in recent_context:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Add the system prompt for the input checker
            messages = [{"role": "system", "content": input_checker_prompt}] + messages
            
            # Add user input
            messages.append({"role": "user", "content": f"Process this user input: {state['user_input']}"})
            
            # Call the input checker agent
            processed_input = call_openai_api(client, messages)
            
            # Update state
            state["processed_input"] = processed_input
            
            return state
        
        # === Primary Agent ===
        def primary_agent(state):
            """Generate a response based on the processed input"""
            # Create messages for primary agent
            messages = []
            
            # Add chat history (except the last user message which we'll add separately)
            if chat_history:
                # Only include the most recent 10 messages to keep within token limits
                recent_messages = chat_history[-10:-1] if len(chat_history) > 10 else chat_history[:-1]
                for msg in recent_messages:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Add the system prompt for the primary agent
            messages = [{"role": "system", "content": system_prompt}] + messages
            
            # Add processed user input
            messages.append({"role": "user", "content": state["processed_input"]})
            
            # Call the primary agent
            response = call_openai_api(client, messages)
            
            # Update state
            state["primary_response"] = response
            
            return state
        
        # === Output Checker Agent ===
        def output_checker(state):
            """Check if the response aligns with the user input and format it consistently"""
            output_checker_prompt = """
            You are a response quality specialist. Your task is to:
            1. Analyze the user's original input and the AI's response
            2. Verify that the response properly addresses the user's question/request
            3. Check for accuracy, completeness, and relevance
            4. Reformat the response to ensure consistency and clarity
            
            If the response doesn't align with the user's input, improve it.
            If the response is appropriate, maintain it but ensure formatting consistency.
            
            Your final response should follow the format of ChatGPT interface. Only output the reformatted text.
            """
            
            # Create messages for output checker
            messages = [
                {"role": "system", "content": output_checker_prompt},
                {"role": "user", "content": f"Original user input: {state['user_input']}\n\nAI response: {state['primary_response']}\n\nPlease check if this response aligns with the user's input and reformat if necessary."}
            ]
            
            # Call the output checker agent
            final_response = call_openai_api(client, messages)
            
            # Update state
            state["final_response"] = final_response
            
            return state
        
        # Define the state schema
        class AgentState(TypedDict):
            user_input: str
            processed_input: str
            primary_response: str
            final_response: str
        
        # Define the graph structure with schema
        workflow = StateGraph(AgentState)
        
        # Add nodes to the graph
        workflow.add_node("input_checker", input_checker)
        workflow.add_node("primary_agent", primary_agent)
        workflow.add_node("output_checker", output_checker)
        
        # Connect the nodes
        workflow.add_edge("input_checker", "primary_agent")
        workflow.add_edge("primary_agent", "output_checker")
        workflow.add_edge("output_checker", END)
        
        # Set the entry point
        workflow.set_entry_point("input_checker")
        
        # Compile the graph
        graph = workflow.compile()
        
        # Run the workflow
        final_state = graph.invoke(state)
        
        # Return the final response
        return final_state["final_response"]
        
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