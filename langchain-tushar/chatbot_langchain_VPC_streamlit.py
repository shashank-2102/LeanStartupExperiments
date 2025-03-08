import streamlit as st
import os
from dotenv import load_dotenv
from typing import Literal
from typing_extensions import TypedDict
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

# Page configuration
st.set_page_config(page_title="VPC Chatbot", layout="wide")

# Load environment variables
load_dotenv()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "agent_outputs" not in st.session_state:
    st.session_state.agent_outputs = {}
    
if "graph" not in st.session_state:
    st.session_state.graph = None

# Define agent names
MEMBERS = ["Input_Checker", "VPC", "Output_Checker"]
OPTIONS = MEMBERS + ["FINISH"]

# Router class for structured output
class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""
    next: Literal[*OPTIONS]

# Search tool function
@tool
def search_for_business_insights(query: str) -> str:
    """
    Search the web for business insights, market trends, and competitive analysis.
    """
    try:
        tavily_tool = TavilySearchResults(max_results=5)
        search_results = tavily_tool.invoke(query)
        
        formatted_results = "## Web Search Results\n\n"
        for i, result in enumerate(search_results, 1):
            formatted_results += f"### Result {i}: {result.get('title', 'No Title')}\n"
            formatted_results += f"{result.get('content', 'No content available')}\n\n"
            formatted_results += f"Source: {result.get('url', 'No URL')}\n\n"
            formatted_results += "---\n\n"
        
        return formatted_results
    except Exception as e:
        return f"Error searching: {str(e)}"

def setup_graph():
    """Set up the agent graph with all nodes and connections"""
    
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)
    
    # Define State class
    class State(MessagesState):
        next: str
    
    # System prompt for supervisor
    system_prompt = """You are a supervisor agent coordinating the creation of a Value Proposition Canvas.
    Route to Input_Checker first, then VPC, then Output_Checker, then FINISH."""
    
    # Define node functions
    def supervisor_node(state: State) -> Command[Literal[*MEMBERS, "__end__"]]:
        messages = [
            {"role": "system", "content": system_prompt},
        ] + state["messages"]
        response = llm.with_structured_output(Router).invoke(messages)
        goto = response["next"]
        if goto == "FINISH":
            goto = END
    
        return Command(goto=goto, update={"next": goto})
    
    # Create agents
    input_agent = create_react_agent(
        llm, tools=[], 
        prompt="""You are the Input Checker. Verify if the user's input aligns with business creation 
        and specifically towards creating a value proposition canvas. Keep your response concise."""
    )
    
    VPC_agent = create_react_agent(
        llm, tools=[search_for_business_insights], 
        prompt="""You are the Value Proposition Canvas creator. Utilize the user's requirements 
        and search tools to create a comprehensive value proposition canvas. Clearly mention 
        what information you take from internet searches. Set seed to 123 for consistency."""
    )
    
    output_agent = create_react_agent(
        llm, tools=[], 
        prompt="""You are the Output Checker. Review the VPC output to ensure it properly 
        addresses the user's query with accurate and helpful information. Be concise."""
    )
    
    # Node functions for agent processing
    def input_node(state: State) -> Command[Literal["supervisor"]]:
        result = input_agent.invoke(state)
        return Command(
            update={"messages": [HumanMessage(content=result["messages"][-1].content, name="Input_Checker")]},
            goto="VPC",
        )
    
    def VPC_node(state: State) -> Command[Literal["supervisor"]]:
        result = VPC_agent.invoke(state)
        return Command(
            update={"messages": [HumanMessage(content=result["messages"][-1].content, name="VPC")]},
            goto="Output_Checker",
        )
    
    def output_node(state: State) -> Command[Literal["supervisor"]]:
        result = output_agent.invoke(state)
        return Command(
            update={"messages": [HumanMessage(content=result["messages"][-1].content, name="Output_Checker")]},
            goto="supervisor",
        )
    
    # Build the graph
    builder = StateGraph(State)
    builder.add_edge(START, "supervisor")
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("Input_Checker", input_node)
    builder.add_node("VPC", VPC_node)
    builder.add_node("Output_Checker", output_node)
    
    return builder.compile()

def sidebar_settings():
    """Display and handle sidebar API settings"""
    with st.sidebar:
        st.title("🔑 API Settings")
        openai_key = st.text_input("OpenAI API Key:", type="password", 
                                  value=os.getenv("OPENAI_API_KEY", ""))
        tavily_key = st.text_input("Tavily API Key:", type="password", 
                                  value=os.getenv("TAVILY_API_KEY", ""))
        
        init_button = st.button("Initialize Chatbot", type="primary")
        
        if init_button:
            if openai_key and tavily_key:
                os.environ["OPENAI_API_KEY"] = openai_key
                os.environ["TAVILY_API_KEY"] = tavily_key
                
                with st.spinner("Setting up the agents..."):
                    try:
                        st.session_state.graph = setup_graph()
                        st.success("✅ Chatbot initialized successfully!")
                        return True
                    except Exception as e:
                        st.error(f"❌ Error initializing chatbot: {str(e)}")
                        return False
            else:
                st.error("⚠️ Please provide both API keys")
                return False
        
        # Help information
        st.markdown("---")
        st.markdown("""
        ### How it works
        
        This chatbot uses multiple agents:
        - **Input Checker** verifies your business inquiry
        - **VPC Creator** builds your Value Proposition Canvas
        - **Output Checker** ensures quality results
        
        Enter your business idea in the chat to get started.
        """)
                
    return st.session_state.graph is not None

def process_chat_input(user_input: str):
    """Process user input through the agent graph and display streaming results"""
    if not st.session_state.graph:
        st.error("Please initialize the chatbot first using the sidebar!")
        return
        
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Process with graph
    input_data = {"messages": [("user", user_input)]}
    
    # Create chat message container for assistant response
    with st.chat_message("assistant"):
        # Create tabs for viewing different parts
        tab_names = ["Final Response"] + MEMBERS
        tabs = st.tabs(tab_names)
        
        # Placeholders for responses
        placeholders = {name: tabs[i].empty() for i, name in enumerate(tab_names)}
        
        # Processing indicator
        status = st.empty()
        status.info("Processing your request...")
        
        # Reset agent outputs for this conversation turn
        st.session_state.agent_outputs = {}
        
        # Stream the responses
        for s in st.session_state.graph.stream(input_data, subgraphs=True):
            if isinstance(s, tuple) and len(s) > 1:
                for key, value in s[1].items():
                    if key in MEMBERS:
                        if "messages" in value:
                            message = value["messages"][-1]
                            response_text = message.content
                            
                            # Store and display the agent output
                            st.session_state.agent_outputs[key] = response_text
                            placeholders[key].markdown(response_text)
                            
                            # Update the final response tab with all completed outputs
                            final_text = ""
                            for agent, text in st.session_state.agent_outputs.items():
                                final_text += f"### {agent}\n{text}\n\n---\n\n"
                            placeholders["Final Response"].markdown(final_text)
                    
                    elif key == "supervisor" and "next" in value:
                        next_node = value["next"]
                        if next_node != "__end__":
                            status.info(f"📝 Agent working: {next_node}")
        
        # Final status update
        status.success("✅ Processing complete!")
        
        # Save final response to chat history
        final_response = ""
        for agent, text in st.session_state.agent_outputs.items():
            final_response += f"### {agent}\n{text}\n\n---\n\n"
        
        st.session_state.messages.append({"role": "assistant", "content": final_response})

def main():
    st.title("🚀 Value Proposition Canvas Chatbot")
    st.markdown("""
    This multi-agent chatbot helps you create a detailed Value Proposition Canvas for your business idea.
    Enter your business concept below to get started.
    """)
    
    # Initialize sidebar settings
    initialized = sidebar_settings()
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    user_input = st.chat_input("Describe your business idea...", disabled=not initialized)
    if user_input:
        process_chat_input(user_input)

if __name__ == "__main__":
    main()