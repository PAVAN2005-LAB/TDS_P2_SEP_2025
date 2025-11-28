from langgraph.graph import StateGraph, END, START
from langchain_core.rate_limiters import InMemoryRateLimiter
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools import get_rendered_html, download_file, post_request, run_code, add_dependencies
from typing import TypedDict, Annotated, List, Any
from langchain.chat_models import init_chat_model
from langgraph.graph.message import add_messages
import os
from dotenv import load_dotenv

# Load environment variables from .env file (e.g., EMAIL, SECRET, API keys)
load_dotenv()

# Required credentials loaded from the environment
EMAIL = os.getenv("EMAIL")
SECRET = os.getenv("SECRET")

# -------------------------------------------------
# 💾 STATE DEFINITION
# -------------------------------------------------
# Define the state object for the LangGraph. This is passed between nodes.
class AgentState(TypedDict):
    """
    State for the autonomous quiz-solving agent.
    
    messages: The list of messages (history) in the conversation.
    The 'Annotated' type with 'add_messages' ensures any new messages returned
    by a node are automatically appended to the existing list, maintaining
    the full conversation history for the LLM.
    """
    messages: Annotated[List, add_messages]

# List of all available external tools the LLM can call.
TOOLS = [run_code, get_rendered_html, download_file, post_request, add_dependencies]


# -------------------------------------------------
# 🤖 GEMINI LLM SETUP
# -------------------------------------------------
# Implement a custom rate limiter to ensure API usage stays within limits
# (e.g., 9 requests per minute, or 9/60 requests per second).
rate_limiter = InMemoryRateLimiter(
    requests_per_second=9/60,    
    check_every_n_seconds=1,    
    max_bucket_size=9    
)

# Initialize the Chat Model (Gemini 2.5 Flash is efficient for tool-calling/reasoning).
# The model is bound to the TOOLS list, enabling Gemini's structured Tool Calling capability.
llm = init_chat_model(
    model_provider="google_genai",
    model="gemini-2.5-flash",
    rate_limiter=rate_limiter
).bind_tools(TOOLS)    


# -------------------------------------------------
# 📜 SYSTEM PROMPT & CHAIN
# -------------------------------------------------
# Detailed instructions guiding the agent's behavior, goal, and constraints.
# This prompt is critical for reliable multi-step autonomous operation.
SYSTEM_PROMPT = f"""
You are an autonomous quiz-solving agent.
... (The detailed rules and instructions) ...
- Email: {EMAIL}
- Secret: {SECRET}

YOUR JOB:
- Follow pages exactly.
- Extract data reliably.
- Never guess.
- Submit correct answers.
- Continue until no new URL.
- Then respond with: END
"""

# Create the full prompt template using the system prompt and a placeholder 
# for the message history (which comes from the State).
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="messages")
])

# Define the runnable chain: Prompt -> LLM.
# This chain is invoked by the 'agent_node'.
llm_with_prompt = prompt | llm


# -------------------------------------------------
# 🧠 AGENT NODE (The Reasoning Step)
# -------------------------------------------------
def agent_node(state: AgentState):
    """
    The main reasoning node where the LLM decides the next action.
    It takes the full message history and outputs either a text response 
    (for reasoning or "END") or a structured tool call.
    """
    # Invoke the LLM chain with the current state's messages.
    result = llm_with_prompt.invoke({"messages": state["messages"]})
    
    # Return the updated state by appending the LLM's response to the history.
    # The 'add_messages' reducer handles the list concatenation automatically.
    return {"messages": state["messages"] + [result]}


# -------------------------------------------------
# ⚙️ GRAPH DEFINITION AND FLOW CONTROL
# -------------------------------------------------
def route(state):
    """
    Conditional edge function that determines the next step based on the 
    last message from the 'agent' node. This is the flow control logic.
    """
    last = state["messages"][-1]
    
    # Check robustly for tool calls (supports different message object types)
    tool_calls = None
    if hasattr(last, "tool_calls"):
        tool_calls = getattr(last, "tool_calls", None)
    elif isinstance(last, dict):
        tool_calls = last.get("tool_calls")

    if tool_calls:
        # If the LLM requested tool execution, go to the tool execution node.
        return "tools"
    
    # Check robustly for the terminal condition "END".
    content = None
    if hasattr(last, "content"):
        content = getattr(last, "content", None)
    elif isinstance(last, dict):
        content = last.get("content")

    # If the LLM's text output is exactly "END", terminate the graph execution.
    if isinstance(content, str) and content.strip() == "END":
        return END
    
    # Handle cases where the content might be a list (e.g., text output combined with tool output).
    if isinstance(content, list) and content[0].get("text").strip() == "END":
        return END
        
    # If no tool call and not "END", go back to the agent (e.g., for self-correction or reasoning).
    return "agent"

# Initialize the LangGraph StateGraph with the defined state object.
graph = StateGraph(AgentState)

# Add the main reasoning node.
graph.add_node("agent", agent_node)

# Add the Tool execution node. ToolNode is a pre-built node that executes 
# the tool calls requested by the LLM and formats the output.
graph.add_node("tools", ToolNode(TOOLS))


# Define the edges (connections) between nodes:

# 1. Start: The graph always begins by routing the initial user message (URL) to the agent.
graph.add_edge(START, "agent")

# 2. Tool-Use Loop: After the tools execute, send the results back to the agent 
#    so the LLM can read the output and decide the next step.
graph.add_edge("tools", "agent")

# 3. Decision Maker: Route the agent's output conditionally using the 'route' function.
graph.add_conditional_edges(
    "agent",    # The source node for the conditional routing
    route       # The function that determines the next destination
)

# Compile the graph into an executable application.
app = graph.compile()


# -------------------------------------------------
# 🧪 TEST FUNCTION
# -------------------------------------------------
def run_agent(url: str) -> str:
    """
    Executes the compiled LangGraph application with a starting URL.
    """
    # Invoke the graph with the initial state: the user's message containing the URL.
    app.invoke({
        "messages": [{"role": "user", "content": url}]},
        # Set a high recursion limit for multi-step, complex problems.
        config={"recursion_limit": 200}, 
    )
    # This print statement assumes the END state was reached successfully.
    print("Tasks completed succesfully")
