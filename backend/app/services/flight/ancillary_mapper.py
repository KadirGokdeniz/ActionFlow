"""
Ancillary (ek hizmet) mapper - Bagaj ve diğer ek hizmetler.
"""
from typing import List, Any
from app.models.flight_models import Ancillary


def map_baggage_ancillaries(raw_offer: Any) -> List[Ancillary]:
    """
    Uçuş teklifindeki ek bagaj hizmetlerini Ancillary listesine dönüştürür.

    Bu fonksiyon SADECE raw Amadeus flight offer bekler.
    Beklenmeyen input gelirse güvenli şekilde boş liste döner.

    Args:
        raw_offer: Raw Amadeus flight offer (dict)

    Returns:
        List[Ancillary]: Ek hizmetler listesi
    """

    # 🛑 Guard clause – yanlış tip
    if not isinstance(raw_offer, dict):
        return []

    price = raw_offer.get("price")
    if not isinstance(price, dict):
        return []

    services = price.get("otherServices")
    if not isinstance(services, list):
        return []

    ancillaries: List[Ancillary] = []

    for s in services:
        if not isinstance(s, dict):
            continue

        ancillaries.append(
            Ancillary(
                type=s.get("type", "BAGGAGE"),
                description=s.get("description", ""),
                price=float(s.get("amount", 0) or 0),
                currency=s.get("currency", "EUR"),
            )
        )

    return ancillaries
