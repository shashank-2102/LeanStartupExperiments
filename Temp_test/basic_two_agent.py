import os
import openai
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("Missing OPENAI_API_KEY.")

# Messages

# Instructions for each agent.
task_prompt = "The user can give you a range of business ideas, normal ones like creating new types of toys to outlandish ones like organic gmo pet food for parrots. You should entertain these ideas as long as they are about the business idea and its value proposition (canvas) or VPC. If it deviates to other tasks then it is out of scope. Do not be extremely strict."
with open("prompts/Agent_A_Test.txt", "r", encoding='utf-8') as file:
    prompt = file.read()
agent_a_instruction = prompt + f"\n {task_prompt}"

with open("prompts/prompt_VPC_CUT.txt", "r", encoding='utf-8') as file:
    prompt = file.read()
agent_b_instruction = prompt

# Map agent names to their system instructions.
agents = {
    "Agent A": agent_a_instruction,
    "Agent B": agent_b_instruction,
}

messages = [{"role": "user", "content": "Hi"}] #starting message
context_variables = {}
conversation_summary = ""  

def run_agent(agent_name, input_message, messages=messages, context_variables=context_variables, conversation_summary=conversation_summary):
    """
    Calls the OpenAI ChatCompletion API with the agent's system instruction and a single user message.
    """
    system_message = {"role": "system", "content": agents[agent_name]}
    messages = [
        system_message,
        {"role": "user", "content": f"NEW USER INPUT {input_message} \n EXISTING CONTECT {messages}"},
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0.9,
            max_tokens=250,
        )
    except Exception as e:
        print(f"Error calling OpenAI API for {agent_name}: {e}")
        return None

    reply = response.choices[0].message.content.strip()
    return reply

def conversation_loop():
    print("Starting conversation. Type 'quit' to exit.\n")
    
    while True:
        print(f"Messages {messages}")
    
        user_input = input("User: ").strip()
        if user_input.lower() == "quit":
            print("Conversation ended.")
            break

        # Agent A processes the user input.
        agent_a_output = run_agent("Agent A", user_input)
        if agent_a_output is None:
            print("Agent A failed to get a response.\n")
            continue  # Skip to the next iteration
        
        print(f"\nAgent A output: {agent_a_output}")

        # If the output is one of the special cases, print a message and go back to user input.
        if agent_a_output.lower() == "[request clarification input]":
            print("Agent A output: Please clarify or rephrase your request and try again.\n")
            continue  # Return to start of the loop

        elif agent_a_output.lower() == "[sorry, input deviates from task. please try again]":
            print("Agent A output: Conversation deviates from scope, try again.\n")
            continue  # Return to start of the loop
        
        else:
            # Otherwise, proceed with Agent B.
            agent_b_output = run_agent("Agent B", agent_a_output)
            if agent_b_output is None:
                print("Agent B failed to get a response.\n")
                continue
            print(f"\nAgent B output: {agent_b_output}\n")
            messages.append({"role": "system", "content": agent_b_output})


if __name__ == "__main__":
    conversation_loop()
