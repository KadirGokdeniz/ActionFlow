"""
Amadeus booking yanıtlarını dönüştüren mapper.
"""
from typing import Optional


def map_booking_response(raw_response: dict) -> dict:
    """
    Amadeus booking yanıtını sözlük yapısına dönüştürür.
    
    Test'lerin beklediği format:
    {
        "order_id": str,
        "pnr": str | None,
        "passengers": [{"first_name": str, "last_name": str}, ...]
    }
    """
    
    # PNR'ı associatedRecords'dan çıkar
    pnr: Optional[str] = None
    records = raw_response.get("associatedRecords", [])
    if records:
        pnr = records[0].get("reference")
    
    # Yolcu bilgilerini dönüştür
    passengers = []
    for traveler in raw_response.get("travelers", []):
        name = traveler.get("name", {})
        passengers.append({
            "first_name": name.get("firstName", ""),
            "last_name": name.get("lastName", ""),
        })
    
    return {
        "order_id": raw_response.get("id"),
        "pnr": pnr,
        "passengers": passengers,
    }