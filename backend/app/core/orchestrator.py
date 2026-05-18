"""
ActionFlow AI - LangGraph Orchestrator v4
Multi-agent workflow for travel customer support

Architecture:
    User → Supervisor (initial routing only)
              ↓
    ┌─────────────────────────────────────────┐
    │  Sharpener (self-contained loop)        │
    └─────────────────────────────────────────┘
              ↓ (plan_ready)
         Supervisor → Action Agent
    
States:
    IDLE → SHARPENING → READY_FOR_ACTION → ACTION → COMPLETED
    
MCP Client: Tools are called via MCP Server
"""

import logging
from typing import Optional, List
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# Imports from new modules
from app.core.schemas import AgentState, TravelContext, ConversationState
from app.core.utils import create_empty_travel_context
from app.core.tools import all_tools, mcp_client

# Import Agents
from app.agents.supervisor import supervisor_node
from app.agents.intent_sharpener import intent_sharpener_node
from app.agents.info_agent import info_agent_node
from app.agents.action_agent import action_agent_node

logger = logging.getLogger("ActionFlow-Orchestrator-v4")


# ═══════════════════════════════════════════════════════════════════
# ESCALATION NODE (Small enough to keep here for now or move later)
# ═══════════════════════════════════════════════════════════════════

async def escalation_node(state: AgentState) -> dict:
    """
    Escalation - Hands off to human support
    """
    logger.info("🚨 [ESCALATION] Preparing handoff...")
    
    travel_context = state.get("travel_context") or {}
    
    # Summarize what we know
    summary_parts = ["📋 Collected Info:"]
    if travel_context.get("destination"):
        summary_parts.append(f"  • Destination: {travel_context['destination']}")
    if travel_context.get("departure_date"):
        summary_parts.append(f"  • Dates: {travel_context.get('departure_date')} - {travel_context.get('return_date', '?')}")
    if travel_context.get("travelers"):
        summary_parts.append(f"  • Travelers: {travel_context['travelers']}")
    
    summary = "\n".join(summary_parts) if len(summary_parts) > 1 else ""
    
    response_text = f"""I understand, I'm connecting you to a customer representative.

{summary}

Your request has been recorded. We will get back to you as soon as possible.
Could you please share your contact information? (phone or email)
"""
    
    return {
        "messages": [AIMessage(content=response_text)],
        "current_state": ConversationState.ESCALATION
    }


# ═══════════════════════════════════════════════════════════════════
# ROUTING LOGIC
# ═══════════════════════════════════════════════════════════════════

def route_from_supervisor(state: AgentState) -> str:
    """Routes based on supervisor decision"""
    return state.get("next_agent", "end")


def route_after_agent(state: AgentState) -> str:
    """Routes after agent execution - check for tool calls"""
    messages = state.get("messages", [])
    if not messages:
        return "supervisor"
    
    last_message = messages[-1]
    
    # Check if there are tool calls to execute
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info("🔧 Routing to tools node")
        return "tools"
    
    return "supervisor"


def route_after_sharpener(state: AgentState) -> str:
    """Routes after Sharpener - based on plan_ready flag"""
    if state.get("plan_ready"):
        logger.info("📍 Sharpener done, plan ready → supervisor (for action routing)")
        return "supervisor"
    else:
        # Needs more user input - end turn, wait for next message
        logger.info("📍 Sharpener needs more info → end (wait for user)")
        return "end"


# ═══════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════

def build_graph(checkpointer=None):
    """
    Builds the LangGraph workflow v4
    """
    logger.info("🏗️ Building LangGraph workflow v4...")
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("sharpener", intent_sharpener_node)
    workflow.add_node("info", info_agent_node)
    workflow.add_node("action", action_agent_node)
    workflow.add_node("escalation", escalation_node)
    workflow.add_node("tools", ToolNode(all_tools))
    
    # Entry point
    workflow.set_entry_point("supervisor")
    
    # Supervisor routing (main router)
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "sharpener": "sharpener",
            "info": "info",
            "action": "action",
            "escalation": "escalation",
            "end": END
        }
    )
    
    # Sharpener routing (self-contained loop logic)
    workflow.add_conditional_edges(
        "sharpener",
        route_after_sharpener,
        {
            "supervisor": "supervisor",  # Plan ready, go to action
            "end": END                    # Need user input, end turn
        }
    )
    
    # Info Agent → Tools or Supervisor
    workflow.add_conditional_edges(
        "info",
        route_after_agent,
        {"tools": "tools", "supervisor": "supervisor"}
    )
    
    # Action Agent → Tools or Supervisor
    workflow.add_conditional_edges(
        "action",
        route_after_agent,
        {"tools": "tools", "supervisor": "supervisor"}
    )
    
    # Escalation → END
    workflow.add_edge("escalation", END)
    
    # Tools → Supervisor (for result processing)
    workflow.add_edge("tools", "supervisor")
    
    # Compile
    app = workflow.compile(checkpointer=checkpointer)
    logger.info("✅ Orchestrator v4 compiled successfully")
    
    return app


# ═══════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

_compiled_graph = None


def get_graph(checkpointer=None):
    """Returns compiled graph (singleton)"""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph(checkpointer)
    return _compiled_graph


async def chat(
    message: str,
    customer_id: str = "anonymous",
    conversation_history: Optional[List[BaseMessage]] = None,
    travel_context: Optional[TravelContext] = None,
    # State persistence parameters
    current_state: Optional[str] = None,
    plan_ready: bool = False,
    sharpening_turns: int = 0,
    action_turns: int = 0,
    completed_tasks: Optional[List[str]] = None  # ← ADDED!
) -> dict:
    """
    Chat interface
    """
    graph = get_graph()
    
    messages = conversation_history or []
    messages.append(HumanMessage(content=message))
    
    # Restore state from string
    restored_state = ConversationState.IDLE
    if current_state:
        try:
            if isinstance(current_state, str):
                state_name = current_state.replace("ConversationState.", "")
                restored_state = ConversationState(state_name.lower())
            else:
                restored_state = current_state
        except (ValueError, KeyError):
            logger.warning(f"Could not restore state: {current_state}, defaulting to IDLE")
            restored_state = ConversationState.IDLE
    
    logger.info(f"🔄 [CHAT] Restored state: {restored_state}, plan_ready: {plan_ready}, turns: {sharpening_turns}, tasks: {completed_tasks or []}")
    
    initial_state = {
        "messages": messages,
        "customer_id": customer_id,
        "current_state": restored_state,
        "previous_state": None,
        "travel_context": travel_context or create_empty_travel_context(),
        "intent": None,
        "intent_category": None,
        "next_agent": None,
        "plan_ready": plan_ready,
        "needs_user_input": False,
        "sharpening_turns": sharpening_turns,
        "action_turns": action_turns,
        "awaiting_confirmation": False,
        "suggestions": [],
        "completed_tasks": completed_tasks or [],  # ← FIXED!
        "language": "en"
    }
    
    result = await graph.ainvoke(initial_state)
    
    # Get last AI message
    response_text = None
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            response_text = msg.content
            break
    
    if not response_text:
        response_text = "Sorry, an error occurred. Please try again."
    
    # Convert enum to string for JSON serialization
    current_state_str = result.get("current_state")
    if isinstance(current_state_str, ConversationState):
        current_state_str = current_state_str.value
    
    return {
        "response": response_text,
        "state": {
            "travel_context": result.get("travel_context"),
            "current_state": current_state_str,
            "plan_ready": result.get("plan_ready", False),
            "sharpening_turns": result.get("sharpening_turns", 0),
            "action_turns": result.get("action_turns", 0),
            "intent_category": result.get("intent_category"),
            "completed_tasks": result.get("completed_tasks", []),
            "suggestions": result.get("suggestions", [])
        },
        "suggestions": result.get("suggestions", [])
    }


async def shutdown():
    """Cleanup"""
    await mcp_client.close()
    logger.info("🛑 Orchestrator v4 shutdown complete")


__all__ = [
    "get_graph",
    "build_graph",
    "chat",
    "shutdown",
    "mcp_client",
    "AgentState",
    "TravelContext",
    "ConversationState"
]