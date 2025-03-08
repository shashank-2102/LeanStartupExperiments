import getpass
import os
from dotenv import load_dotenv
from typing import Annotated
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
from typing import Literal
from typing_extensions import TypedDict
#from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, END
from langgraph.types import Command
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
import os
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent


def _set_if_undefined(var: str):
    if not os.getenv(var):
        os.environ[var] = getpass.getpass(f"Please provide your {var}")
        #print("API key error")

_set_if_undefined("OPENAI_API_KEY")
_set_if_undefined("TAVILY_API_KEY")

tavily_tool = TavilySearchResults(max_results=5)

def load_prompt(file_name: str, name: str):
    with open(f"prompts/{file_name}.txt", "r", encoding='utf-8') as file:
        name = file.read()
    return name

members = ["Input_Checker", "VPC", "Output_Checker"]
# Our team supervisor is an LLM node. It just picks the next agent to process
# and decides when the work is completed
options = members + ["FINISH"]

VPC_prompt = (
    open("/Users/tushargupta/Developer/LeanStartupExperiments/prompts/prompt_VPC_CUT.txt").read()
)

system_prompt = (
    open("/Users/tushargupta/Developer/LeanStartupExperiments/prompts/VPC_supervisor_tushar.txt").read()
)

class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""

    next: Literal[*options]


llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


class State(MessagesState):
    next: str


def supervisor_node(state: State) -> Command[Literal[*members, "__end__"]]:
    messages = [
        {"role": "system", "content": system_prompt},
    ] + state["messages"]
    response = llm.with_structured_output(Router).invoke(messages)
    goto = response["next"]
    if goto == "FINISH":
        goto = END

    return Command(goto=goto, update={"next": goto})

# Set up Tavily API key
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY", "")  # Make sure to set this in your environment

# Create a Tavily search tool
tavily_search = TavilySearchResults(max_results=5)

@tool
def search_for_business_insights(query: str) -> str:
    """
    Search the web for business insights, market trends, and competitive analysis to help with 
    creating a Value Proposition Canvas.
    
    Args:
        query: A search query related to business ideas, market analysis, customer needs, or competitors.
        
    Returns:
        Relevant information from the web that can help in developing a Value Proposition Canvas.
    """
    search_results = tavily_search.invoke(query)
    
    # Format the results for better readability
    formatted_results = "## Web Search Results\n\n"
    for i, result in enumerate(search_results, 1):
        formatted_results += f"### Result {i}: {result.get('title', 'No Title')}\n"
        formatted_results += f"{result.get('content', 'No content available')}\n\n"
        formatted_results += f"Source: {result.get('url', 'No URL')}\n\n"
        formatted_results += "---\n\n"
    
    return formatted_results


input_agent = create_react_agent(
    llm, tools=[], prompt="""You are the input agent. 
    You are supposed to check the user input if it aligns with the intention of 
    business creation and specifically towards the creaation of value proposition canvas.
    Your output should be sent to only supervisor"""
)

VPC_agent = create_react_agent(
    llm, tools=[search_for_business_insights], prompt="""you are responsible for 
    creating value propisition canvas and ensure to utilise the user's requirement 
    and also the tools and return a tailored response for a value proposition canvas. 
    Ensure that you mention what information you take from the internet. 
    For maintaining unifromity in responses, set seed to 123. 
    Your response should be sent directly to the supervisor agent and not the input agent.""" # CHANGE THE CONTENT OF THE VPC PROMPT
)

output_agent = create_react_agent(
    llm, tools=[], prompt="""You are output agent, you are supposed to oversee whether the supervisor
      provides sane output answering the users' query"""
)

def input_node(state: State) -> Command[Literal["supervisor"]]:
    result = input_agent.invoke(state)
    

    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="Input_Checker")
            ]
        },
        goto="VPC",
    )


def VPC_node(state: State) -> Command[Literal["supervisor"]]:
    result = VPC_agent.invoke(state)
    

    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="VPC")
            ]
        },
        goto="Output_Checker",
    )


def output_node(state: State) -> Command[Literal["supervisor"]]:
    result = output_agent.invoke(state)
    

    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="Output_Checker")
            ]
        },
        goto="supervisor",
    )

builder = StateGraph(State)
builder.add_edge(START, "supervisor")
builder.add_node("supervisor", supervisor_node)
builder.add_node("VPC", VPC_node)
builder.add_node("Input_Checker", input_node)
builder.add_node("Output_Checker", output_node)
graph = builder.compile()


def chatbot(graph):
    results = []

    while True:
        query = input("\033[1m User >>:\033[0m")

        if query.lower() == "quit":
            print("Chatbot: Goodbye!")
            break

        input_data = {"messages": [("user", query)]}
        responses = []

        for s in graph.stream(input_data, subgraphs=True):
            if isinstance(s, tuple) and len(s) > 1:
                for key, value in s[1].items():
                    if key in ["Input_Checker", "VPC", "Output_Checker"]:
                        if "messages" in value:
                            message = value["messages"][-1]
                            response_text = f"{key}: {message.content}"
                            print(response_text)
                            responses.append(response_text)
                    
                    elif key == "supervisor" and "next" in value:
                        next_node = value["next"]
                        if next_node != "__end__":
                            print(f"Calling {next_node}")

        # Append the combined responses to results
        if responses:
            combined_response = "\n".join(responses)
            results.append(combined_response)

chatbot(graph)

