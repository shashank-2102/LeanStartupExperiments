from swarm import Swarm, Agent
import os
from dotenv import load_dotenv

load_dotenv() #get stuff from env

client = Swarm()

def transfer_to_agent_b():
    return agent_b

def transfer_to_agent_a():
    return agent_a

agent_a = Agent(
    name="Agent A",
    instructions="You are a helpful agent that gives healthy food advice. Transfer to agent B if the user asks about icecream.",
    functions=[transfer_to_agent_b],
)

agent_b = Agent(
    name="Agent B",
    instructions="Only speak in Haikus and say you are the icecream expert. If user asks about fitness, transfer to agent A.",
    functions=[transfer_to_agent_a],
)

messages = [{"role": "user", "content": "Hi"}] #starting message
context_variables = {}

response = client.run(
    agent=agent_a,
    messages=messages,
    context_variables=context_variables,
    # stream=True,
)

messages.append({"role": "assistant", "content": response.messages[-1]["content"]})

print(response.messages[-1]["content"])

# Conversation loop for continuous interaction
def conversation_loop():
    current_agent = agent_a  # Start with Agent A
    while True:
        # Get user input
        user_message = input("User: ")
        
        # Check for "quit" to exit the loop
        if user_message.lower() == "quit":
            print("Conversation ended.")
            break
        
        # Append user message to conversation history
        messages.append({"role": "user", "content": user_message})
        
        # Run client with the current agent and updated history
        response = client.run(
            agent=current_agent,
            messages=messages,
            context_variables=context_variables,
            # stream=True,
        )
        
        # Print the agent's response
        agent_reply = response.messages[-1]["content"]
        print(f"{current_agent.name}: {agent_reply}")
        
        # Add agent reply to messages list
        messages.append({"role": "assistant", "content": agent_reply})
        
        # Update `current_agent` if a handoff occurred
        current_agent = response.agent  # This updates if a handoff happened

# Run the conversation loop
conversation_loop()

