from app.services.flight.mappers.mapper import map_baggage_ancillaries
from app.models.flight_models import Ancillary


def test_map_baggage_ancillaries_with_data():
    raw_offer = {
        "price": {
            "otherServices": [
                {
                    "type": "BAGGAGE",
                    "description": "Extra checked baggage",
                    "amount": "50.00",
                    "currency": "EUR"
                }
            ]
        }
    }

    ancillaries = map_baggage_ancillaries(raw_offer)

    assert len(ancillaries) == 1
    ancillary = ancillaries[0]

    assert isinstance(ancillary, Ancillary)
    assert ancillary.type == "BAGGAGE"
    assert ancillary.description == "Extra checked baggage"
    assert ancillary.price == 50.0
    assert ancillary.currency == "EUR"
def test_map_baggage_ancillaries_empty():
    raw_offer = {
        "price": {}
    }

    ancillaries = map_baggage_ancillaries(raw_offer)

    assert ancillaries == []
