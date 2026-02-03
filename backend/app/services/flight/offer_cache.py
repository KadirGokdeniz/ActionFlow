from datetime import datetime, timedelta
from typing import Any, Dict

# In-memory offer cache (raw Amadeus offers only)
_offer_cache: Dict[str, Dict[str, Any]] = {}


def store_offer(offer_id: str, raw_data: dict) -> None:
    """
    Raw Amadeus flight-offer'ı 20 dakika geçerli olacak şekilde saklar.
    """
    if not isinstance(raw_data, dict):
        return

    if raw_data.get("type") != "flight-offer":
        return

    _offer_cache[offer_id] = {
        "raw": raw_data,
        "expires_at": datetime.utcnow() + timedelta(minutes=20)
    }


def get_offer(offer_id: str) -> dict | None:
    """
    Geçerli bir raw Amadeus teklifi varsa döndürür, yoksa None.
    """
    entry = _offer_cache.get(offer_id)
    if not entry:
        return None

    if datetime.utcnow() > entry["expires_at"]:
        del _offer_cache[offer_id]
        return None

    raw = entry.get("raw")
    if not isinstance(raw, dict):
        return None

    return raw


def cache_offers(flights: list) -> None:
    """
    Birden fazla raw Amadeus uçuş teklifini cache'e ekler.
    SADECE raw flight-offer'lar cache'lenir.
    """
    if not isinstance(flights, list):
        return

    for flight in flights:
        if not isinstance(flight, dict):
            continue

        offer_id = flight.get("id")
        if not offer_id:
            continue

        # 🔐 Sadece raw Amadeus flight-offer cache'e girer
        if flight.get("type") != "flight-offer":
            continue

        store_offer(offer_id, flight)


def clear_cache() -> None:
    """Cache'i temizler (test için)."""
    _offer_cache.clear()


def get_cache_size() -> int:
    """Cache'deki teklif sayısını döndürür."""
    return len(_offer_cache)
