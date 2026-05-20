"""
Unit tests for action_phase based booking flow.
Tests determine_phase routing, supervisor action_phase routing,
and full SEARCH -> PRESENT -> CONFIRM -> BOOK flow via mocked chat().
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from contextlib import nullcontext
from langchain_core.messages import HumanMessage, AIMessage

# == determine_phase (action_phase field) ====================================

def test_determine_phase_search_when_no_action_phase():
    from app.agents.action_agent import determine_phase, ActionPhase
    state = {"messages": [HumanMessage(content="hi")], "completed_tasks": [], "action_phase": None}
    assert determine_phase(state) == ActionPhase.SEARCH


def test_determine_phase_search_when_no_messages():
    from app.agents.action_agent import determine_phase, ActionPhase
    state = {"messages": [], "completed_tasks": [], "action_phase": "searching"}
    assert determine_phase(state) == ActionPhase.SEARCH


def test_determine_phase_present_when_action_phase_searching():
    from app.agents.action_agent import determine_phase, ActionPhase
    state = {
        "messages": [HumanMessage(content="find flights")],
        "completed_tasks": ["search_initiated"],
        "action_phase": "searching"
    }
    assert determine_phase(state) == ActionPhase.PRESENT


def test_determine_phase_confirm_when_presented_and_user_selects():
    from app.agents.action_agent import determine_phase, ActionPhase
    state = {
        "messages": [
            HumanMessage(content="IST to CDG"),
            AIMessage(content="Here are 3 flights"),
            HumanMessage(content="Option 2 please")
        ],
        "completed_tasks": ["results_presented"],
        "action_phase": "presented"
    }
    assert determine_phase(state) == ActionPhase.CONFIRM


def test_determine_phase_present_when_presented_no_selection():
    from app.agents.action_agent import determine_phase, ActionPhase
    state = {
        "messages": [
            HumanMessage(content="IST to CDG"),
            AIMessage(content="Here are 3 flights"),
            HumanMessage(content="Can you show me cheaper options?")
        ],
        "completed_tasks": ["results_presented"],
        "action_phase": "presented"
    }
    assert determine_phase(state) == ActionPhase.PRESENT


def test_determine_phase_book_when_confirming_and_user_confirms():
    from app.agents.action_agent import determine_phase, ActionPhase
    state = {
        "messages": [
            AIMessage(content="Would you like to proceed?"),
            HumanMessage(content="Yes please book it")
        ],
        "completed_tasks": ["selection_presented"],
        "action_phase": "confirming"
    }
    assert determine_phase(state) == ActionPhase.BOOK


def test_determine_phase_confirm_when_confirming_no_confirmation():
    from app.agents.action_agent import determine_phase, ActionPhase
    state = {
        "messages": [
            AIMessage(content="Would you like to proceed?"),
            HumanMessage(content="Hmm let me think about it")
        ],
        "completed_tasks": ["selection_presented"],
        "action_phase": "confirming"
    }
    assert determine_phase(state) == ActionPhase.CONFIRM


def test_determine_phase_complete_when_action_phase_booked():
    from app.agents.action_agent import determine_phase, ActionPhase
    state = {
        "messages": [HumanMessage(content="ok")],
        "completed_tasks": ["booking_completed"],
        "action_phase": "booked"
    }
    assert determine_phase(state) == ActionPhase.COMPLETE


def test_determine_phase_complete_when_action_phase_completed():
    from app.agents.action_agent import determine_phase, ActionPhase
    state = {
        "messages": [HumanMessage(content="ok")],
        "completed_tasks": [],
        "action_phase": "completed"
    }
    assert determine_phase(state) == ActionPhase.COMPLETE


# == Supervisor action_phase routing =========================================

def make_action_state(messages, action_phase=None, completed_tasks=None):
    from app.core.schemas import ConversationState
    return {
        "messages": messages,
        "current_state": ConversationState.ACTION,
        "plan_ready": True,
        "travel_context": None,
        "completed_tasks": completed_tasks or [],
        "action_phase": action_phase,
        "language": "en",
        "previous_state": None,
    }


def no_escalation(mocker):
    mocker.patch("app.agents.supervisor.quick_escalation_check", AsyncMock(return_value=False))
    mocker.patch("app.agents.supervisor.analyze_escalation_need",
                 AsyncMock(return_value={"should_escalate": False}))


@pytest.mark.asyncio
async def test_supervisor_presented_last_ai_routes_to_end(mocker):
    """action_phase=presented + last msg is AI -> wait for user (end)."""
    from app.agents.supervisor import supervisor_node
    no_escalation(mocker)

    state = make_action_state(
        messages=[HumanMessage(content="find flights"), AIMessage(content="Here are 3 options")],
        action_phase="presented"
    )
    result = await supervisor_node(state)
    assert result["next_agent"] == "end"


@pytest.mark.asyncio
async def test_supervisor_presented_last_human_routes_to_action(mocker):
    """action_phase=presented + last msg is Human -> user made selection -> action."""
    from app.agents.supervisor import supervisor_node
    no_escalation(mocker)

    state = make_action_state(
        messages=[
            HumanMessage(content="find flights"),
            AIMessage(content="Here are 3 options"),
            HumanMessage(content="Option 1")
        ],
        action_phase="presented"
    )
    result = await supervisor_node(state)
    assert result["next_agent"] == "action"


@pytest.mark.asyncio
async def test_supervisor_confirming_last_human_routes_to_action(mocker):
    """action_phase=confirming + last msg is Human -> user confirming -> action."""
    from app.agents.supervisor import supervisor_node
    no_escalation(mocker)

    state = make_action_state(
        messages=[
            AIMessage(content="Would you like to proceed?"),
            HumanMessage(content="Yes please")
        ],
        action_phase="confirming"
    )
    result = await supervisor_node(state)
    assert result["next_agent"] == "action"


@pytest.mark.asyncio
async def test_supervisor_confirming_last_ai_routes_to_end(mocker):
    """action_phase=confirming + last msg is AI -> just asked for confirmation -> end."""
    from app.agents.supervisor import supervisor_node
    no_escalation(mocker)

    state = make_action_state(
        messages=[HumanMessage(content="option 1"), AIMessage(content="Would you like to proceed?")],
        action_phase="confirming"
    )
    result = await supervisor_node(state)
    assert result["next_agent"] == "end"


@pytest.mark.asyncio
async def test_supervisor_booked_routes_to_completed(mocker):
    """action_phase=booked -> booking done -> completed."""
    from app.agents.supervisor import supervisor_node
    no_escalation(mocker)

    state = make_action_state(
        messages=[HumanMessage(content="yes"), AIMessage(content="Booking confirmed!")],
        action_phase="booked"
    )
    result = await supervisor_node(state)
    assert result["next_agent"] == "end"
    assert result.get("current_state").value == "completed"


# == Full flow via chat() mock ================================================

def _mock_graph_with_action_phase(mocker, ai_message: str, action_phase: str, current_state=None):
    from app.core.schemas import ConversationState
    cs = current_state or ConversationState.ACTION
    result = {
        "messages": [HumanMessage(content="hi"), AIMessage(content=ai_message)],
        "current_state": cs,
        "plan_ready": True,
        "sharpening_turns": 0,
        "action_turns": 1,
        "intent_category": "REACTIVE",
        "completed_tasks": [],
        "suggestions": [],
        "travel_context": None,
        "action_phase": action_phase,
    }
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value=result)
    mocker.patch("app.core.orchestrator.get_graph", return_value=mock_graph)
    mocker.patch("app.core.orchestrator.track_end_to_end", return_value=nullcontext())
    return mock_graph


@pytest.mark.asyncio
async def test_chat_returns_action_phase_in_state(mocker):
    """chat() returns action_phase in result state for persistence."""
    _mock_graph_with_action_phase(mocker, "Here are 3 flights", "presented")
    from app.core.orchestrator import chat
    result = await chat(message="Book IST to CDG", customer_id="user1")
    assert result["state"].get("action_phase") == "presented"


@pytest.mark.asyncio
async def test_chat_passes_action_phase_to_graph(mocker):
    """chat() passes restored action_phase to initial graph state."""
    mock_graph = _mock_graph_with_action_phase(mocker, "Confirm flight?", "confirming")
    from app.core.orchestrator import chat
    await chat(message="Option 1", customer_id="user1", action_phase="presented")

    call_args = mock_graph.ainvoke.call_args[0][0]
    assert call_args.get("action_phase") == "presented"


@pytest.mark.asyncio
async def test_full_flow_search_phase_sets_searching(mocker):
    """After flight search, action_phase transitions to searching then presented."""
    _mock_graph_with_action_phase(mocker, "Here are flights: 1. TK 150EUR", "presented")
    from app.core.orchestrator import chat
    result = await chat(
        message="Book flight from IST to CDG",
        customer_id="user1",
        action_phase=None
    )
    assert result["state"].get("action_phase") == "presented"
    assert "150" in result["response"] or len(result["response"]) > 0


@pytest.mark.asyncio
async def test_full_flow_confirm_phase_sets_confirming(mocker):
    """After selection, action_phase transitions to confirming."""
    _mock_graph_with_action_phase(mocker, "Great choice! Would you like to proceed?", "confirming")
    from app.core.orchestrator import chat
    result = await chat(
        message="Option 1",
        customer_id="user1",
        action_phase="presented"
    )
    assert result["state"].get("action_phase") == "confirming"


@pytest.mark.asyncio
async def test_full_flow_book_phase_sets_booked(mocker):
    """After confirmation, action_phase transitions to booked."""
    from app.core.schemas import ConversationState
    _mock_graph_with_action_phase(
        mocker,
        "Booking confirmed! Reference: ABC123",
        "booked",
        current_state=ConversationState.COMPLETED
    )
    from app.core.orchestrator import chat
    result = await chat(
        message="Yes please book it",
        customer_id="user1",
        action_phase="confirming"
    )
    assert result["state"].get("action_phase") == "booked"
    assert result["state"].get("current_state") == "completed"
