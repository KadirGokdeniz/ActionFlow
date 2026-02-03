# tests/unit/test_offer_cache.py
from app.services.flight.offer_cache import store_offer, get_offer
from datetime import datetime, timedelta
import app.services.flight.offer_cache as cache


def test_store_and_get_offer():
    offer_id = "TEST_OFFER_1"
    raw = {"id": offer_id, "price": {"total": "100"}}

    store_offer(offer_id, raw)
    result = get_offer(offer_id)

    assert result == raw


def test_get_expired_offer():
    offer_id = "EXPIRED_OFFER"
    raw = {"id": offer_id}

    cache._offer_cache[offer_id] = {
        "raw": raw,
        "expires_at": datetime.utcnow() - timedelta(minutes=1)
    }

    result = get_offer(offer_id)

    assert result is None


def test_get_unknown_offer():
    result = get_offer("DOES_NOT_EXIST")
    assert result is None
