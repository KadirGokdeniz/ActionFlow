"""Unit tests for intent_sharpener pure helper functions."""
import pytest
from app.agents.intent_sharpener import (
    create_empty_travel_context,
    get_current_phase,
    check_completion,
    apply_smart_defaults,
    format_collected_info,
    create_plan_summary,
)


def test_create_empty_travel_context_has_required_keys():
    ctx = create_empty_travel_context()
    for key in ("destination", "departure_date", "return_date", "travelers", "collected_fields"):
        assert key in ctx
    assert ctx["travelers"] == 1
    assert ctx["collected_fields"] == []


def test_get_current_phase_1_when_no_destination():
    ctx = create_empty_travel_context()
    assert get_current_phase(ctx) == 1


def test_get_current_phase_2_when_destination_but_no_dates():
    ctx = create_empty_travel_context()
    ctx["destination"] = "Paris"
    ctx["collected_fields"] = ["destination"]
    assert get_current_phase(ctx) == 2


def test_get_current_phase_3_when_destination_and_dates_but_no_budget():
    ctx = create_empty_travel_context()
    ctx["destination"] = "Paris"
    ctx["departure_date"] = "2025-06-01"
    ctx["return_date"] = "2025-06-08"
    ctx["collected_fields"] = ["destination", "departure_date", "return_date"]
    assert get_current_phase(ctx) == 3


def test_get_current_phase_4_when_all_complete():
    ctx = create_empty_travel_context()
    ctx["destination"] = "Paris"
    ctx["departure_date"] = "2025-06-01"
    ctx["return_date"] = "2025-06-08"
    ctx["budget_max"] = 1000
    ctx["collected_fields"] = ["destination", "departure_date", "return_date", "budget_max"]
    assert get_current_phase(ctx) == 4


def test_check_completion_false_when_missing_fields():
    ctx = create_empty_travel_context()
    is_complete, missing = check_completion(ctx)
    assert is_complete is False
    assert "destination" in missing
    assert "departure_date" in missing


def test_check_completion_true_when_all_required_present():
    ctx = create_empty_travel_context()
    ctx["collected_fields"] = ["destination", "departure_date", "return_date"]
    is_complete, missing = check_completion(ctx)
    assert is_complete is True
    assert missing == []


def test_apply_smart_defaults_fills_missing_fields():
    ctx = create_empty_travel_context()
    ctx = apply_smart_defaults(ctx)
    assert ctx["motivation"] == "general"
    assert ctx["budget_currency"] == "EUR"
    assert ctx["travelers"] == 1
    assert ctx["accommodation_pref"] == "hotel"


def test_apply_smart_defaults_does_not_overwrite_existing():
    ctx = create_empty_travel_context()
    ctx["motivation"] = "romantic"
    ctx = apply_smart_defaults(ctx)
    assert ctx["motivation"] == "romantic"


def test_format_collected_info_includes_destination():
    ctx = create_empty_travel_context()
    ctx["destination"] = "Paris"
    ctx["destination_display"] = "Paris, France"
    result = format_collected_info(ctx)
    assert "Paris" in result


def test_format_collected_info_returns_placeholder_when_empty():
    ctx = create_empty_travel_context()
    result = format_collected_info(ctx)
    assert len(result) > 0  # Returns "Henuz bilgi yok" or similar


def test_create_plan_summary_includes_destination_and_dates():
    ctx = create_empty_travel_context()
    ctx["destination"] = "Paris"
    ctx["departure_date"] = "2025-06-01"
    ctx["return_date"] = "2025-06-08"
    summary = create_plan_summary(ctx, language="en")
    assert "Paris" in summary
    assert "2025-06-01" in summary
    assert "2025-06-08" in summary


def test_create_plan_summary_turkish():
    ctx = create_empty_travel_context()
    ctx["destination"] = "Paris"
    ctx["departure_date"] = "2025-06-01"
    ctx["return_date"] = "2025-06-08"
    summary = create_plan_summary(ctx, language="tr")
    assert "Paris" in summary
