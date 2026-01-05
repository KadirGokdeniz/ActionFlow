import os
from typing import Annotated, List, Dict, Any, Optional, Literal
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# ═══════════════════════════════════════════════════════════════════
# CRITICAL CHANGE: Import from services, NOT from main
# This breaks the circular dependency: main -> orchestrator -> main
# ═══════════════════════════════════════════════════════════════════
from services import (
    search_flights_logic, 
    search_hotels_by_city_logic, 
    amadeus_delete
)
from database import vector_search

# ═══════════════════════════════════════════════════════════════════
# STATE DEFINITION
# ═══════════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    customer_id: str
    booking_context: Optional[Dict[str, Any]]
    intent: Optional[str]
    urgency: Optional[str]
    next_agent: Optional[str]

# ═══════════════════════════════════════════════════════════════════
# TOOLS CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Define tools using the logic from services.py
tools = [
    search_flights_logic,
    search_hotels_by_city_logic,
    amadeus_delete,
    vector_search
]

tool_node = ToolNode(tools)

# ═══════════════════════════════════════════════════════════════════
# AGENT NODES
# ═══════════════════════════════════════════════════════════════════

async def call_model(state: AgentState):
    """Main Orchestrator Agent"""
    messages = state["messages"]
    model = ChatOpenAI(model="gpt-4o", streaming=True).bind_tools(tools)
    
    # System prompt to guide the orchestrator
    system_prompt = (
        "You are ActionFlow AI, a specialized travel assistant. "
        "You have access to flight searches, hotel searches, and booking management. "
        "Use the tools provided to answer the user's request accurately."
    )
    
    response = await model.ainvoke([{"role": "system", "content": system_prompt}] + messages)
    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """Router to determine if tools should be called"""
    messages = state["messages"]
    last_message = messages[-1]
    
    if last_message.tool_calls:
        return "tools"
    return END

# ═══════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════

def build_graph():
    """Builds and compiles the LangGraph workflow"""
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    # Set Entry Point
    workflow.set_entry_point("agent")

    # Add Conditional Edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
    )

    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")

    # Compile
    return workflow.compile()