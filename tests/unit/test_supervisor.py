"""
Unit tests for supervisor_node routing decisions.
All LLM and escalation calls are mocked.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

pytestmark = pytest.mark.asyncio


# ?? Helpers ???????????????????????????????????????????????????????????????????

def make_state(messages, current_state=None, plan_ready=False,
               completed_tasks=None, previous_state=None):
    from app.core.schemas import ConversationState
    return {
        "messages": messages,
        "current_state": current_state or ConversationState.IDLE,
        "plan_ready": plan_ready,
        "travel_context": None,
        "completed_tasks": completed_tasks or [],
        "language": "en",
        "previous_state": previous_state,
    }


def mock_llm_response(mocker, category, has_destination=False, has_dates=False):
    resp = MagicMock()
    resp.content = json.dumps({
        "category": category,
        "has_destination": has_destination,
        "has_dates": has_dates,
        "has_travelers": False
    })
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=resp)
    mocker.patch("app.agents.supervisor.llm", mock_llm)


def no_escalation(mocker):
    mocker.patch("app.agents.supervisor.quick_escalation_check", AsyncMock(return_value=False))
    mocker.patch("app.agents.supervisor.analyze_escalation_need",
                 AsyncMock(return_value={"should_escalate": False}))


# ?? No message ????????????????????????????????????????????????????????????????

async def test_no_human_message_routes_to_end():
    """State with no HumanMessage routes to end."""
    from app.agents.supervisor import supervisor_node
    state = make_state([AIMessage(content="Welcome")])
    result = await supervisor_node(state)
    assert result["next_agent"] == "end"


# ?? IDLE routing ???????????????????????????????????????????????????????????????

async def test_idle_planning_routes_to_sharpener(mocker):
    """IDLE + PLANNING intent ? sharpener."""
    from app.agents.supervisor import supervisor_node
    no_escalation(mocker)
    mock_llm_response(mocker, "PLANNING")

    result = await supervisor_node(make_state([HumanMessage(content="I want to travel")]))
    assert result["next_agent"] == "sharpener"


async def test_idle_reactive_with_details_routes_to_action(mocker):
    """IDLE + REACTIVE + destination + date ? action with plan_ready=True."""
    from app.agents.supervisor import supervisor_node
    no_escalation(mocker)
    mock_llm_response(mocker, "REACTIVE", has_destination=True, has_dates=True)

    result = await supervisor_node(
        make_state([HumanMessage(content="Book Paris flight on March 15th")])
    )
    assert result["next_agent"] == "action"
    assert result.get("plan_ready") is True


async def test_idle_info_query_routes_to_info_agent(mocker):
    """IDLE + INFO intent ? info agent."""
    from app.agents.supervisor import supervisor_node
    no_escalation(mocker)
    mock_llm_response(mocker, "INFO")

    result = await supervisor_node(
        make_state([HumanMessage(content="What is your cancellation policy?")])
    )
    assert result["next_agent"] == "info"


async def test_idle_llm_json_error_defaults_to_sharpener(mocker):
    """IDLE + invalid LLM JSON response ? defaults to sharpener."""
    from app.agents.supervisor import supervisor_node
    no_escalation(mocker)

    bad = MagicMock()
    bad.content = "not valid json"
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=bad)
    mocker.patch("app.agents.supervisor.llm", mock_llm)

    result = await supervisor_node(make_state([HumanMessage(content="test")]))
    assert result["next_agent"] == "sharpener"


# ?? Escalation ?????????????????????????????????????????????????????????????????

async def test_explicit_escalation_overrides_routing(mocker):
    """Explicit human request always routes to escalation regardless of state."""
    from app.agents.supervisor import supervisor_node
    mocker.patch("app.agents.supervisor.quick_escalation_check", AsyncMock(return_value=True))

    result = await supervisor_node(
        make_state([HumanMessage(content="I want to speak to a human agent")])
    )
    assert result["next_agent"] == "escalation"


async def test_sentiment_escalation_during_action(mocker):
    """Frustration detected in ACTION state triggers escalation."""
    from app.agents.supervisor import supervisor_node
    from app.core.schemas import ConversationState

    mocker.patch("app.agents.supervisor.quick_escalation_check", AsyncMock(return_value=False))
    mocker.patch("app.agents.supervisor.analyze_escalation_need",
                 AsyncMock(return_value={"should_escalate": True, "reason": "frustration"}))

    result = await supervisor_node(
        make_state([HumanMessage(content="This is terrible!")],
                   current_state=ConversationState.ACTION)
    )
    assert result["next_agent"] == "escalation"


# ?? SHARPENING routing ?????????????????????????????????????????????????????????

async def test_sharpening_plan_ready_routes_to_action(mocker):
    """SHARPENING + plan_ready=True ? action."""
    from app.agents.supervisor import supervisor_node
    from app.core.schemas import ConversationState
    no_escalation(mocker)

    result = await supervisor_node(
        make_state([HumanMessage(content="Yes those dates work")],
                   current_state=ConversationState.SHARPENING, plan_ready=True)
    )
    assert result["next_agent"] == "action"


async def test_sharpening_not_ready_stays_in_sharpening(mocker):
    """SHARPENING + plan_ready=False ? stays in sharpener."""
    from app.agents.supervisor import supervisor_node
    from app.core.schemas import ConversationState
    no_escalation(mocker)

    result = await supervisor_node(
        make_state([HumanMessage(content="Hmm not sure yet")],
                   current_state=ConversationState.SHARPENING, plan_ready=False)
    )
    assert result["next_agent"] == "sharpener"


# ?? ACTION routing ?????????????????????????????????????????????????????????????

async def test_action_results_presented_routes_to_end(mocker):
    """ACTION + action_phase=presented + last msg is AIMessage ? end (wait for user)."""
    from app.agents.supervisor import supervisor_node
    from app.core.schemas import ConversationState
    from langchain_core.messages import AIMessage
    no_escalation(mocker)

    state = make_state([HumanMessage(content="search"), AIMessage(content="Here are flights")],
                       current_state=ConversationState.ACTION,
                       completed_tasks=[])
    state["action_phase"] = "presented"

    result = await supervisor_node(state)
    assert result["next_agent"] == "end"


# ?? INFO routing ???????????????????????????????????????????????????????????????

async def test_info_state_from_sharpening_returns_to_sharpener(mocker):
    """INFO state (came from SHARPENING) ? back to sharpener after answer."""
    from app.agents.supervisor import supervisor_node
    from app.core.schemas import ConversationState
    no_escalation(mocker)

    result = await supervisor_node(
        make_state([HumanMessage(content="Got it thanks")],
                   current_state=ConversationState.INFO,
                   previous_state=ConversationState.SHARPENING)
    )
    assert result["next_agent"] == "sharpener"
