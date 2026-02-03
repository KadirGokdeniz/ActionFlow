"""
Amadeus API yanıtlarını iç modellere dönüştüren mapper fonksiyonları.
"""
from typing import List, Optional
from app.models.flight_models import (
    FlightOffer,
    FlightSegment,
    BaggageInfo,
    BookingResult,
    Ancillary,
)


def map_amadeus_offer(raw_offer: dict) -> FlightOffer:
    """Amadeus flight-offers yanıtını FlightOffer modeline dönüştürür."""
    
    price_data = raw_offer.get("price", {})
    
    # Segmentleri dönüştür
    segments: List[FlightSegment] = []
    for itinerary in raw_offer.get("itineraries", []):
        for seg in itinerary.get("segments", []):
            segments.append(FlightSegment(
                origin=seg["departure"]["iataCode"],
                destination=seg["arrival"]["iataCode"],
                departure=seg["departure"]["at"],
                arrival=seg["arrival"]["at"],
                carrier=seg["carrierCode"],
                flight_number=seg["number"],
                duration=seg.get("duration", ""),
            ))
    
    # Bagaj bilgisini çıkar
    baggage = _extract_baggage(raw_offer)
    
    # Fare brand (varsa)
    fare_brand = _extract_fare_brand(raw_offer)
    
    return FlightOffer(
        offer_id=raw_offer.get("id", "unknown"),
        price=float(price_data.get("total", 0)),
        currency=price_data.get("currency", "EUR"),
        segments=segments,
        baggage=baggage,
        fare_brand=fare_brand,
    )


def _extract_baggage(raw_offer: dict) -> Optional[BaggageInfo]:
    """travelerPricings içinden bagaj bilgisini çıkarır."""
    traveler_pricings = raw_offer.get("travelerPricings", [])
    
    if not traveler_pricings:
        return None
    
    fare_details = traveler_pricings[0].get("fareDetailsBySegment", [])
    
    if not fare_details:
        return None
    
    checked_bags = fare_details[0].get("includedCheckedBags")
    
    if not checked_bags:
        return None
    
    return BaggageInfo(
        quantity=checked_bags.get("quantity", 0),
        weight=checked_bags.get("weight"),
        unit=checked_bags.get("weightUnit"),
    )


def _extract_fare_brand(raw_offer: dict) -> Optional[str]:
    """travelerPricings içinden fare brand bilgisini çıkarır."""
    traveler_pricings = raw_offer.get("travelerPricings", [])
    
    if not traveler_pricings:
        return None
    
    fare_details = traveler_pricings[0].get("fareDetailsBySegment", [])
    
    if not fare_details:
        return None
    
    return fare_details[0].get("fareBasis")


def map_booking_response(raw_response: dict) -> BookingResult:
    """Amadeus booking yanıtını BookingResult modeline dönüştürür."""
    
    # PNR'ı associatedRecords'dan çıkar
    pnr = None
    records = raw_response.get("associatedRecords", [])
    if records:
        pnr = records[0].get("reference")
    
    # Fiyat bilgisi
    price_data = raw_response.get("flightOffers", [{}])[0].get("price", {})
    
    return BookingResult(
        order_id=raw_response.get("id", ""),
        status="CONFIRMED" if raw_response.get("id") else "FAILED",
        ticketed=raw_response.get("ticketingAgreement", {}).get("option") == "CONFIRM",
        total_price=float(price_data.get("total", 0)),
        currency=price_data.get("currency", "EUR"),
        warnings=[w.get("detail", "") for w in raw_response.get("warnings", [])],
    )


def map_baggage_ancillaries(raw_offer: dict) -> List[Ancillary]:
    """Ek bagaj hizmetlerini Ancillary listesine dönüştürür."""
    
    services = raw_offer.get("price", {}).get("otherServices", [])
    
    return [
        Ancillary(
            type=s.get("type", "BAGGAGE"),
            description=s.get("description", ""),
            price=float(s.get("amount", 0)),
            currency=s.get("currency", "EUR"),
        )
        for s in services
    ]