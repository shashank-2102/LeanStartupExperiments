"""
Enhanced Agent module for multi-agent chatbot system
Handles communication with OpenAI API with agent context awareness
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

def get_agent_response(user_input, system_prompt, chat_history, current_agent_name=None):
    """
    Get a response from the agent using OpenAI API with enhanced LangGraph structure
    
    Args:
        user_input (str): The user's input message
        system_prompt (str): The system prompt for the agent
        chat_history (list): The chat history (may contain messages from multiple agents)
        current_agent_name (str): Name of the current agent
        
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
        
        # Define the enhanced LangGraph state
        state = {
            "user_input": user_input,
            "processed_input": "",
            "context_summary": "",
            "primary_response": "",
            "final_response": "",
            "current_agent": current_agent_name or "Assistant"
        }
        
        # === Context Analyzer Agent ===
        def context_analyzer(state):
            """Analyze the conversation context, especially multi-agent interactions"""
            context_prompt = f"""
            You are a conversation context specialist for {state['current_agent']}. Your task is to:
            1. Analyze the conversation history for context from multiple agents
            2. Identify what previous agents have discussed
            3. Note any ongoing topics or unresolved questions
            4. Provide a context summary for the current agent
            
            Current agent: {state['current_agent']}
            
            Your output should be a brief context summary highlighting:
            - Key topics discussed by previous agents
            - Any information gaps or follow-up questions
            - Relevant context for the current query
            """
            
            # Create messages for context analysis
            messages = [{"role": "system", "content": context_prompt}]
            
            # Add recent chat history with agent information
            if chat_history:
                recent_context = chat_history[-10:] if len(chat_history) >= 10 else chat_history
                for msg in recent_context:
                    role = msg["role"]
                    content = msg["content"]
                    agent = msg.get("agent", "Unknown")
                    
                    if role == "assistant":
                        # Include agent information in the context
                        content_with_agent = f"[{agent}]: {content}"
                        messages.append({"role": "assistant", "content": content_with_agent})
                    else:
                        messages.append({"role": role, "content": content})
            
            messages.append({"role": "user", "content": f"Analyze this context for the current query: {state['user_input']}"})
            
            try:
                context_summary = call_openai_api(client, messages, temperature=0.3, max_tokens=300)
                state["context_summary"] = context_summary
            except Exception as e:
                state["context_summary"] = f"Context analysis unavailable: {str(e)}"
            
            return state
        
        # === Input Processor Agent ===
        def input_processor(state):
            """Process the user input with context awareness"""
            processor_prompt = f"""
            You are an input processing specialist for {state['current_agent']}. Your task is to:
            1. Analyze the user's input considering the conversation context
            2. Rephrase it to be clearer and more specific
            3. Include relevant context from the conversation
            4. Format it optimally for the current agent's processing
            
            Context Summary: {state['context_summary']}
            Current Agent: {state['current_agent']}
            
            Your output should be a well-structured query that includes all necessary context.
            """
            
            messages = [
                {"role": "system", "content": processor_prompt},
                {"role": "user", "content": f"Process this input: {state['user_input']}"}
            ]
            
            try:
                processed_input = call_openai_api(client, messages, temperature=0.3, max_tokens=400)
                state["processed_input"] = processed_input
            except Exception as e:
                state["processed_input"] = state['user_input']  # Fallback to original input
            
            return state
        
        # === Primary Agent ===
        def primary_agent(state):
            """Generate a response as the current agent with full context awareness"""
            # Enhanced system prompt with agent switching awareness
            enhanced_system_prompt = f"""
            {system_prompt}
            
            IMPORTANT CONTEXT AWARENESS:
            - You are {state['current_agent']}
            - This conversation may have involved other AI agents previously
            - Build upon previous responses while maintaining your unique perspective
            - If asked about previous responses from other agents, acknowledge them respectfully
            - Maintain conversation continuity while bringing your specialized expertise
            
            Context from previous interactions: {state['context_summary']}
            """
            
            # Create messages for the primary agent
            messages = [{"role": "system", "content": enhanced_system_prompt}]
            
            # Add relevant chat history (last 8 messages to avoid token limits)
            if chat_history:
                recent_messages = chat_history[-8:] if len(chat_history) > 8 else chat_history[:-1]  # Exclude current user message
                for msg in recent_messages:
                    role = msg["role"]
                    content = msg["content"]
                    agent = msg.get("agent")
                    
                    if role == "assistant" and agent and agent != state['current_agent']:
                        # Slightly modify assistant messages from other agents for context
                        content = f"[Previous response from {agent}]: {content}"
                    
                    messages.append({"role": role, "content": content})
            
            # Add the processed user input
            messages.append({"role": "user", "content": state["processed_input"]})
            
            try:
                response = call_openai_api(client, messages, temperature=0.7, max_tokens=800)
                state["primary_response"] = response
            except Exception as e:
                state["primary_response"] = f"I apologize, but I encountered an error: {str(e)}"
            
            return state
        
        # === Response Refiner Agent ===
        def response_refiner(state):
            """Refine and polish the response for consistency"""
            refiner_prompt = f"""
            You are a response quality specialist for {state['current_agent']}. Your task is to:
            1. Review the agent's response for clarity and completeness
            2. Ensure it addresses the user's query appropriately
            3. Check for consistency with the agent's role and expertise
            4. Polish the formatting and tone
            5. Ensure smooth integration with the multi-agent conversation flow
            
            Current Agent: {state['current_agent']}
            Original Query: {state['user_input']}
            Context: {state['context_summary']}
            
            Maintain the agent's voice while ensuring high quality output.
            """
            
            messages = [
                {"role": "system", "content": refiner_prompt},
                {"role": "user", "content": f"Refine this response: {state['primary_response']}"}
            ]
            
            try:
                final_response = call_openai_api(client, messages, temperature=0.3, max_tokens=800)
                state["final_response"] = final_response
            except Exception as e:
                state["final_response"] = state["primary_response"]  # Fallback to primary response
            
            return state
        
        # Define the enhanced state schema
        class EnhancedAgentState(TypedDict):
            user_input: str
            processed_input: str
            context_summary: str
            primary_response: str
            final_response: str
            current_agent: str
        
        # Build the enhanced workflow
        workflow = StateGraph(EnhancedAgentState)
        
        # Add nodes
        workflow.add_node("context_analyzer", context_analyzer)
        workflow.add_node("input_processor", input_processor)
        workflow.add_node("primary_agent", primary_agent)
        workflow.add_node("response_refiner", response_refiner)
        
        # Connect the nodes
        workflow.add_edge("context_analyzer", "input_processor")
        workflow.add_edge("input_processor", "primary_agent")
        workflow.add_edge("primary_agent", "response_refiner")
        workflow.add_edge("response_refiner", END)
        
        # Set entry point
        workflow.set_entry_point("context_analyzer")
        
        # Compile and run the workflow
        graph = workflow.compile()
        final_state = graph.invoke(state)
        
        return final_state["final_response"]
        
    except Exception as e:
        # Handle API errors gracefully
        print(f"Error in enhanced agent processing: {str(e)}")
        
        # Provide user-friendly error messages
        if "auth" in str(e).lower() or "api key" in str(e).lower():
            return "Authentication error: The OpenAI API key may be invalid. Please update your API key in the configuration panel."
        elif "timeout" in str(e).lower() or "connect" in str(e).lower():
            return "Connection error: Unable to connect to OpenAI's servers. Please check your internet connection and try again."
        elif "rate" in str(e).lower() or "quota" in str(e).lower():
            return "Rate limit exceeded: Please wait a moment before sending another message."
        else:
            return f"I apologize, but I encountered an error: {str(e)}. Please try again or contact support if the issue persists."

def get_simple_agent_response(user_input, system_prompt, chat_history):
    """
    Get a simple response without the enhanced LangGraph processing (fallback method)
    
    Args:
        user_input (str): The user's input message
        system_prompt (str): The system prompt for the agent
        chat_history (list): The chat history
        
    Returns:
        str: The agent's response
    """
    try:
        client = get_openai_client()
        
        # Simple message structure
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent chat history (last 6 messages)
        if chat_history:
            recent_messages = chat_history[-6:] if len(chat_history) > 6 else chat_history[:-1]
            for msg in recent_messages:
                role = msg["role"]
                content = msg["content"]
                agent = msg.get("agent", "Assistant")
                
                if role == "assistant":
                    # Add agent context for multi-agent conversations
                    content = f"[{agent}]: {content}"
                
                messages.append({"role": role, "content": content})
        
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        # Get response
        response = call_openai_api(client, messages)
        return response
        
    except Exception as e:
        return f"I apologize, but I encountered an error: {str(e)}. Please try again."