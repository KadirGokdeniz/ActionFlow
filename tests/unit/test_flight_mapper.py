from backend.app.services.flight.mappers.mapper import map_amadeus_offer
from backend.app.models.flight_models import FlightOffer


def test_map_amadeus_offer_basic():
    raw_offer = {
        "id": "TEST123",
        "price": {
            "total": "199.99",
            "currency": "EUR"
        },
        "itineraries": [
            {
                "segments": [
                    {
                        "departure": {
                            "iataCode": "IST",
                            "at": "2024-12-01T10:00"
                        },
                        "arrival": {
                            "iataCode": "AMS",
                            "at": "2024-12-01T13:00"
                        },
                        "carrierCode": "TK",
                        "number": "1951",
                        "duration": "PT3H"
                    }
                ]
            }
        ],
        "travelerPricings": [
            {
                "fareDetailsBySegment": [
                    {
                        "includedCheckedBags": {
                            "quantity": 1
                        }
                    }
                ]
            }
        ]
    }
    

    offer = map_amadeus_offer(raw_offer)

    # --- type check ---
    assert isinstance(offer, FlightOffer)

    # --- basic fields ---
    assert offer.offer_id == "TEST123"
    assert offer.price == 199.99
    assert offer.currency == "EUR"

    # --- segments ---
    assert len(offer.segments) == 1
    segment = offer.segments[0]
    assert segment.origin == "IST"
    assert segment.destination == "AMS"
    assert segment.carrier == "TK"
    assert segment.flight_number == "1951"

    # --- baggage ---
    assert offer.baggage is not None
    assert offer.baggage.quantity == 1

def test_map_amadeus_offer_without_baggage():
    raw_offer = {
        "id": "TEST_NO_BAG",
        "price": {
            "total": "150.00",
            "currency": "USD"
        },
        "itineraries": [
            {
                "segments": [
                    {
                        "departure": {
                            "iataCode": "JFK",
                            "at": "2024-12-05T08:00"
                        },
                        "arrival": {
                            "iataCode": "LAX",
                            "at": "2024-12-05T11:00"
                        },
                        "carrierCode": "AA",
                        "number": "100",
                        "duration": "PT6H"
                    }
                ]
            }
        ],
        "travelerPricings": [{}]
    }

    offer = map_amadeus_offer(raw_offer)

    assert offer.baggage is None
