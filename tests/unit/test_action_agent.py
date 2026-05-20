"""Unit tests for action_agent pure helper functions."""
import pytest
from unittest.mock import MagicMock
from langchain_core.messages import HumanMessage, AIMessage

# ?? determine_phase ???????????????????????????????????????????????????????????

def test_determine_phase_search_when_no_messages():
    from app.agents.action_agent import determine_phase, ActionPhase
    assert determine_phase({"messages": [], "completed_tasks": []}) == ActionPhase.SEARCH


def test_determine_phase_present_after_search_initiated():
    from app.agents.action_agent import determine_phase, ActionPhase
    state = {
        "messages": [HumanMessage(content="find flights")],
        "completed_tasks": ["search_initiated"]
    }
    assert determine_phase(state) == ActionPhase.PRESENT


def test_determine_phase_complete_when_booking_done():
    from app.agents.action_agent import determine_phase, ActionPhase
    state = {
        "messages": [HumanMessage(content="ok")],
        "completed_tasks": ["booking_completed"]
    }
    assert determine_phase(state) == ActionPhase.COMPLETE


# ?? _detect_user_selection ????????????????????????????????????????????????????

def test_detect_user_selection_number():
    from app.agents.action_agent import _detect_user_selection
    msgs = [HumanMessage(content="I want option 2")]
    result = _detect_user_selection(msgs)
    assert result is not None
    assert result["value"] == 2


def test_detect_user_selection_ordinal_first():
    from app.agents.action_agent import _detect_user_selection
    msgs = [HumanMessage(content="The first one please")]
    result = _detect_user_selection(msgs)
    assert result is not None
    assert result["value"] == 1


def test_detect_user_selection_turkish_ilk():
    from app.agents.action_agent import _detect_user_selection
    msgs = [HumanMessage(content="ilk secenegi istiyorum")]
    result = _detect_user_selection(msgs)
    assert result is not None


def test_detect_user_selection_none_when_no_selection():
    from app.agents.action_agent import _detect_user_selection
    msgs = [HumanMessage(content="I am not sure yet")]
    result = _detect_user_selection(msgs)
    assert result is None


# ?? _detect_user_confirmation ?????????????????????????????????????????????????

def test_detect_confirmation_yes():
    from app.agents.action_agent import _detect_user_confirmation
    assert _detect_user_confirmation([HumanMessage(content="yes please")]) is True


def test_detect_confirmation_turkish_evet():
    from app.agents.action_agent import _detect_user_confirmation
    assert _detect_user_confirmation([HumanMessage(content="evet, tamam")]) is True


def test_detect_confirmation_false_when_no_keyword():
    from app.agents.action_agent import _detect_user_confirmation
    assert _detect_user_confirmation([HumanMessage(content="maybe later")]) is False


# ?? _check_ai_content ?????????????????????????????????????????????????????????

def test_check_ai_content_true_when_content():
    from app.agents.action_agent import _check_ai_content
    msg = AIMessage(content="Here are the results")
    assert _check_ai_content(msg) is True


def test_check_ai_content_false_when_tool_calls():
    from app.agents.action_agent import _check_ai_content
    msg = MagicMock()
    msg.content = "calling tool"
    msg.tool_calls = [{"name": "search_flights"}]
    assert _check_ai_content(msg) is False


def test_check_ai_content_false_when_none():
    from app.agents.action_agent import _check_ai_content
    assert _check_ai_content(None) is False


# ?? _handle_complete_phase ????????????????????????????????????????????????????

@pytest.mark.asyncio
async def test_complete_phase_english():
    from app.agents.action_agent import _handle_complete_phase
    result = await _handle_complete_phase({"language": "en", "completed_tasks": []})
    assert "complete" in result["messages"][0].content.lower()


@pytest.mark.asyncio
async def test_complete_phase_turkish():
    from app.agents.action_agent import _handle_complete_phase
    result = await _handle_complete_phase({"language": "tr", "completed_tasks": []})
    content = result["messages"][0].content
    assert "tamamland" in content.lower() or "rezervasyon" in content.lower()
