from app.services.flight.mappers.booking_mapper import map_booking_response


def test_map_booking_response_basic():
    raw_response = {
        "id": "ORDER123",
        "associatedRecords": [
            {
                "reference": "PNR001",
                "originSystemCode": "GDS"
            }
        ],
        "travelers": [
            {
                "id": "1",
                "name": {
                    "firstName": "Ali",
                    "lastName": "Yilmaz"
                }
            }
        ]
    }

    result = map_booking_response(raw_response)

    assert result["order_id"] == "ORDER123"
    assert result["pnr"] == "PNR001"
    assert result["passengers"][0]["first_name"] == "Ali"
    assert result["passengers"][0]["last_name"] == "Yilmaz"
def test_map_booking_response_without_pnr():
    raw_response = {
        "id": "ORDER_NO_PNR",
        "travelers": []
    }

    result = map_booking_response(raw_response)

    assert result["order_id"] == "ORDER_NO_PNR"
    assert result["pnr"] is None
