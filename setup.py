import streamlit as st
from swarm import Swarm, Agent
import os
from dotenv import load_dotenv

def get_prompt(file_name):
    """Get text from a .txt file and return it"""
    try:
        prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
        file_path = os.path.join(prompts_dir, file_name)
        with open(file_path, "r") as file:
            prompt = file.read()
        return prompt
    except FileNotFoundError:
        st.error(f"Prompt file not found: {file_name}")
        return ""


def init_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        # st.session_state.messages = [{"role": "user", "content": "Hi"}]
        st.session_state.messages = []
    if 'current_agent' not in st.session_state:
        st.session_state.current_agent = None
    if 'client' not in st.session_state:
        st.session_state.client = Swarm()

def transfer_to_agent_b():
    return agent_b

def transfer_to_agent_a():
    return agent_a


agent_a = Agent(
    name="Agent A",
    instructions="Transfer to agent B if user asks about Business Model Canvas" + 
                get_prompt("prompt_VPC.txt"),
    functions=[transfer_to_agent_b],
)

agent_b = Agent(
    name="Agent B",
    instructions="Transfer to agent A if user asks about Value Proposition Canvas" + 
                get_prompt("BMC_combined_3Rs_structure.txt"),
    functions=[transfer_to_agent_a],
)


st.title("Lean Startup Assistant")

# Load environment variables
load_dotenv()

# Initialize session state
init_session_state()


# Initialize current agent if not set
if st.session_state.current_agent is None:
    st.session_state.current_agent = agent_a
    # Get initial response
    if len(st.session_state.messages) == 1:  # Only the initial "Hi" message
        response = st.session_state.client.run(
            agent=agent_a,
            messages=st.session_state.messages,
            context_variables={}
        )
        st.session_state.messages.append({
            "role": "assistant",
            "content": response.messages[-1]["content"]
        })

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to know about Lean Startup methodology?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)

    # Get bot response
    with st.spinner('Thinking...'):
        response = st.session_state.client.run(
            agent=st.session_state.current_agent,
            messages=st.session_state.messages,
            context_variables={},
        )
    
    placeholder = response.messages[-1]["content"]

    # Update current agent if handoff occurred
    st.session_state.current_agent = response.agent
    
    # Display assistant response
    with st.chat_message("assistant"):
        st.write(placeholder)

    def summary(content):

        client = Swarm()

        summariser = Agent(
        name="summariser",
        instructions=f"Summarise the {content} in at most 300 words",
        )

        response = client.run(
            agent=summariser,
            messages=[{"role": "user", "content": "call summariser"}],
        )

        return response.messages[-1]["content"]

    
    # Add assistant response to chat history
    st.session_state.messages.append({
        "role": "assistant",
        "content": summary(response.messages[-1]["content"])
    })

    # Add a sidebar with information
    with st.sidebar:
        st.header("Current Context")
        st.write(f"Speaking with: {st.session_state.current_agent.name}")
        
        if st.session_state.current_agent.name == "Agent A":
            st.write("Current Focus: Value Proposition Canvas")
        else:
            st.write("Current Focus: Business Model Canvas")
        
        # Add a reset button
        if st.button("Reset Conversation"):
            st.session_state.messages = [{"role": "user", "content": "Hi"}]
            st.session_state.current_agent = agent_a
            st.experimental_rerun()

