def map_amadeus_error(error: dict) -> tuple[int, dict]:
    code = error.get("code", "AMADEUS_ERROR")
    detail = error.get("detail", "Unexpected error")

    if "availability" in detail.lower():
        return 409, {
            "code": "NO_AVAILABILITY",
            "message": "Seçilen uçuş artık müsait değil. Lütfen tekrar arama yapın."
        }

    if "price" in detail.lower():
        return 409, {
            "code": "PRICE_CHANGED",
            "message": "Uçuş fiyatı değişti. Lütfen fiyatı tekrar doğrulayın."
        }

    return 400, {
        "code": code,
        "message": detail
    }
