"""
Unit tests for the LangGraph orchestrator.
Tests routing functions, escalation node, and chat() interface.
graph.ainvoke is mocked ? no LLM or network calls.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from contextlib import nullcontext
from langchain_core.messages import HumanMessage, AIMessage

# ?? Routing functions (pure, no mocks needed) ?????????????????????????????????

def test_route_from_supervisor_returns_next_agent():
    from app.core.orchestrator import route_from_supervisor
    assert route_from_supervisor({"next_agent": "action"}) == "action"
    assert route_from_supervisor({"next_agent": "sharpener"}) == "sharpener"
    assert route_from_supervisor({"next_agent": "escalation"}) == "escalation"


def test_route_from_supervisor_defaults_to_end():
    from app.core.orchestrator import route_from_supervisor
    assert route_from_supervisor({}) == "end"


def test_route_after_agent_routes_to_tools_when_tool_calls_present():
    from app.core.orchestrator import route_after_agent
    msg = MagicMock()
    msg.tool_calls = [{"name": "search_flights"}]
    assert route_after_agent({"messages": [msg]}) == "tools"


def test_route_after_agent_routes_to_supervisor_when_no_tool_calls():
    from app.core.orchestrator import route_after_agent
    msg = AIMessage(content="Here are the results")
    assert route_after_agent({"messages": [msg]}) == "supervisor"


def test_route_after_agent_routes_to_supervisor_when_no_messages():
    from app.core.orchestrator import route_after_agent
    assert route_after_agent({"messages": []}) == "supervisor"
    assert route_after_agent({}) == "supervisor"


def test_route_after_sharpener_returns_supervisor_when_plan_ready():
    from app.core.orchestrator import route_after_sharpener
    assert route_after_sharpener({"plan_ready": True}) == "supervisor"


def test_route_after_sharpener_returns_end_when_not_ready():
    from app.core.orchestrator import route_after_sharpener
    assert route_after_sharpener({"plan_ready": False}) == "end"
    assert route_after_sharpener({}) == "end"


# ?? escalation_node ???????????????????????????????????????????????????????????

@pytest.mark.asyncio
async def test_escalation_node_returns_ai_message():
    from app.core.orchestrator import escalation_node
    result = await escalation_node({"travel_context": {}, "completed_tasks": []})
    assert "messages" in result
    assert isinstance(result["messages"][0], AIMessage)


@pytest.mark.asyncio
async def test_escalation_node_includes_destination_in_summary():
    from app.core.orchestrator import escalation_node
    result = await escalation_node({
        "travel_context": {"destination": "Paris", "departure_date": "2025-06-01"},
        "completed_tasks": []
    })
    content = result["messages"][0].content
    assert "Paris" in content


# ?? chat() ????????????????????????????????????????????????????????????????????

def _mock_graph(mocker, ai_message: str = "Test response", extra_state: dict = None):
    """Helper: mock get_graph to return a controlled ainvoke result."""
    from app.core.schemas import ConversationState

    result = {
        "messages": [HumanMessage(content="hi"), AIMessage(content=ai_message)],
        "current_state": ConversationState.IDLE,
        "plan_ready": False,
        "sharpening_turns": 0,
        "action_turns": 0,
        "intent_category": None,
        "completed_tasks": [],
        "suggestions": [],
        "travel_context": None,
        **(extra_state or {})
    }
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value=result)
    mocker.patch("app.core.orchestrator.get_graph", return_value=mock_graph)
    mocker.patch("app.core.orchestrator.track_end_to_end", return_value=nullcontext())
    return mock_graph


@pytest.mark.asyncio
async def test_chat_returns_response_text(mocker):
    """chat() extracts the last AIMessage content as response."""
    _mock_graph(mocker, ai_message="Hello! How can I help?")
    from app.core.orchestrator import chat
    result = await chat(message="Hi", customer_id="user1")
    assert result["response"] == "Hello! How can I help?"
    assert "state" in result


@pytest.mark.asyncio
async def test_chat_returns_fallback_when_no_ai_message(mocker):
    """chat() returns fallback text when graph produces no AIMessage."""
    from app.core.schemas import ConversationState
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={
        "messages": [HumanMessage(content="hi")],
        "current_state": ConversationState.IDLE,
        "plan_ready": False, "sharpening_turns": 0, "action_turns": 0,
        "intent_category": None, "completed_tasks": [], "suggestions": [],
        "travel_context": None
    })
    mocker.patch("app.core.orchestrator.get_graph", return_value=mock_graph)
    mocker.patch("app.core.orchestrator.track_end_to_end", return_value=nullcontext())

    from app.core.orchestrator import chat
    result = await chat(message="Hi")
    assert "error" in result["response"].lower() or len(result["response"]) > 0


@pytest.mark.asyncio
async def test_chat_state_restoration_from_string(mocker):
    """chat() correctly restores ConversationState from string."""
    from app.core.schemas import ConversationState
    mock_graph = _mock_graph(mocker)

    from app.core.orchestrator import chat
    await chat(message="Hi", current_state="sharpening")

    call_args = mock_graph.ainvoke.call_args[0][0]
    assert call_args["current_state"] == ConversationState.SHARPENING


@pytest.mark.asyncio
async def test_chat_defaults_to_idle_for_unknown_state(mocker):
    """chat() falls back to IDLE for unrecognized state strings."""
    from app.core.schemas import ConversationState
    mock_graph = _mock_graph(mocker)

    from app.core.orchestrator import chat
    await chat(message="Hi", current_state="nonexistent_state")

    call_args = mock_graph.ainvoke.call_args[0][0]
    assert call_args["current_state"] == ConversationState.IDLE


@pytest.mark.asyncio
async def test_chat_passes_completed_tasks_to_graph(mocker):
    """chat() passes completed_tasks from caller to initial state."""
    mock_graph = _mock_graph(mocker)

    from app.core.orchestrator import chat
    await chat(message="Hi", completed_tasks=["results_presented"])

    call_args = mock_graph.ainvoke.call_args[0][0]
    assert "results_presented" in call_args["completed_tasks"]
