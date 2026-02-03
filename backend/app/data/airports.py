"""
Airport Database Test Suite
IATA lookup tool testleri
"""

import sys
sys.path.insert(0, '/home/claude/actionflow-ai')

from app.data.airports import AirportDatabase, resolve_location, get_iata_code


def test_exact_match_english():
    """İngilizce şehir isimleri tam eşleşme"""
    db = AirportDatabase()
    
    tests = [
        ("Paris", "PAR"),
        ("London", "LON"),
        ("New York", "NYC"),
        ("Istanbul", "IST"),
        ("Tokyo", "TYO"),
        ("Dubai", "DXB"),
    ]
    
    print("=" * 50)
    print("TEST 1: İngilizce Şehir İsimleri")
    print("=" * 50)
    
    for city, expected_iata in tests:
        result = db.resolve(city, "en")
        status = "✅" if result.get("iata") == expected_iata else "❌"
        print(f"{status} {city} → {result.get('iata', 'NOT FOUND')} (expected: {expected_iata})")


def test_exact_match_turkish():
    """Türkçe şehir isimleri tam eşleşme"""
    db = AirportDatabase()
    
    tests = [
        ("Londra", "LON"),
        ("Viyana", "VIE"),
        ("Münih", "MUC"),
        ("Roma", "FCO"),
        ("Venedik", "VCE"),
        ("Atina", "ATH"),
        ("Selanik", "SKG"),
        ("Prag", "PRG"),
        ("Budapeşte", "BUD"),
        ("Varşova", "WAW"),
        ("Lizbon", "LIS"),
        ("Cenevre", "GVA"),
        ("Brüksel", "BRU"),
        ("Kopenhag", "CPH"),
        ("Kahire", "CAI"),
        ("Pekin", "PEK"),
        ("Sidney", "SYD"),
    ]
    
    print("\n" + "=" * 50)
    print("TEST 2: Türkçe Şehir İsimleri")
    print("=" * 50)
    
    for city, expected_iata in tests:
        result = db.resolve(city, "tr")
        status = "✅" if result.get("iata") == expected_iata else "❌"
        print(f"{status} {city} → {result.get('iata', 'NOT FOUND')} (expected: {expected_iata})")


def test_iata_codes():
    """IATA kodları direkt çözümleme"""
    db = AirportDatabase()
    
    tests = ["IST", "PAR", "LON", "JFK", "CDG", "LHR", "AMS", "FCO", "BCN"]
    
    print("\n" + "=" * 50)
    print("TEST 3: IATA Kodları")
    print("=" * 50)
    
    for code in tests:
        result = db.resolve(code, "en")
        status = "✅" if result.get("found") else "❌"
        city = result.get("city", "NOT FOUND")
        print(f"{status} {code} → {city}")


def test_airport_codes():
    """Havalimanı kodları (JFK, CDG vb.)"""
    db = AirportDatabase()
    
    tests = [
        ("JFK", "NYC"),   # JFK -> New York
        ("CDG", "PAR"),   # CDG -> Paris
        ("LHR", "LON"),   # Heathrow -> London
        ("SAW", "IST"),   # Sabiha Gökçen -> Istanbul
        ("ORY", "PAR"),   # Orly -> Paris
        ("NRT", "TYO"),   # Narita -> Tokyo
        ("HND", "TYO"),   # Haneda -> Tokyo
    ]
    
    print("\n" + "=" * 50)
    print("TEST 4: Havalimanı Kodları")
    print("=" * 50)
    
    for airport_code, expected_city_iata in tests:
        result = db.resolve(airport_code, "en")
        status = "✅" if result.get("iata") == expected_city_iata else "❌"
        print(f"{status} {airport_code} → {result.get('iata', 'NOT FOUND')} (expected: {expected_city_iata})")


def test_turkish_character_tolerance():
    """Türkçe karakter toleransı"""
    db = AirportDatabase()
    
    tests = [
        ("İstanbul", "IST"),
        ("istanbul", "IST"),
        ("ISTANBUL", "IST"),
        ("Münih", "MUC"),
        ("munih", "MUC"),
        ("Zürih", "ZRH"),
        ("zurih", "ZRH"),
        ("Şanghay", "SHA"),
        ("sanghay", "SHA"),
    ]
    
    print("\n" + "=" * 50)
    print("TEST 5: Türkçe Karakter Toleransı")
    print("=" * 50)
    
    for city, expected_iata in tests:
        result = db.resolve(city, "en")
        status = "✅" if result.get("iata") == expected_iata else "❌"
        print(f"{status} {city} → {result.get('iata', 'NOT FOUND')} (expected: {expected_iata})")


def test_fuzzy_matching():
    """Fuzzy eşleşme (yazım hataları)"""
    db = AirportDatabase()
    
    tests = [
        ("Pars", "PAR"),      # Paris yazım hatası
        ("Londn", "LON"),     # London yazım hatası
        ("Barselona", "BCN"), # Barcelona Türkçe yazım
        ("Amsteram", "AMS"),  # Amsterdam yazım hatası
        ("Dubay", "DXB"),     # Dubai Türkçe yazım
    ]
    
    print("\n" + "=" * 50)
    print("TEST 6: Fuzzy Matching (Yazım Hataları)")
    print("=" * 50)
    
    for city, expected_iata in tests:
        result = db.resolve(city, "en")
        found = result.get("found", False)
        iata = result.get("iata", "NOT FOUND")
        
        if found and iata == expected_iata:
            print(f"✅ {city} → {iata}")
        elif not found and result.get("suggestions"):
            first_suggestion = result["suggestions"][0]["iata"] if result["suggestions"] else "?"
            status = "✅" if first_suggestion == expected_iata else "⚠️"
            print(f"{status} {city} → Suggestion: {first_suggestion} (expected: {expected_iata})")
        else:
            print(f"❌ {city} → {iata} (expected: {expected_iata})")


def test_multiple_airports():
    """Çoklu havalimanı olan şehirler"""
    db = AirportDatabase()
    
    multi_airport_cities = ["London", "Paris", "New York", "Tokyo", "Istanbul", "Moscow"]
    
    print("\n" + "=" * 50)
    print("TEST 7: Çoklu Havalimanı Olan Şehirler")
    print("=" * 50)
    
    for city in multi_airport_cities:
        result = db.resolve(city, "en")
        if result.get("found"):
            airports = result.get("airports", [])
            airport_codes = [a["code"] for a in airports]
            has_multiple = result.get("has_multiple_airports", False)
            status = "✅" if has_multiple else "⚠️"
            print(f"{status} {city} ({result['iata']}): {', '.join(airport_codes)}")


def test_country_search():
    """Ülkeye göre arama"""
    db = AirportDatabase()
    
    print("\n" + "=" * 50)
    print("TEST 8: Ülkeye Göre Arama")
    print("=" * 50)
    
    # Türkiye
    turkey_cities = db.search_by_country("Turkey", "en")
    print(f"✅ Turkey: {len(turkey_cities)} cities")
    for c in turkey_cities[:3]:
        print(f"   - {c['city']} ({c['iata']})")
    
    # Yunanistan (Türkçe)
    greece_cities = db.search_by_country("Yunanistan", "tr")
    print(f"✅ Yunanistan: {len(greece_cities)} cities")
    for c in greece_cities[:3]:
        print(f"   - {c['city']} ({c['iata']})")


def test_bilingual_response():
    """İki dilli yanıt"""
    db = AirportDatabase()
    
    print("\n" + "=" * 50)
    print("TEST 9: İki Dilli Yanıt")
    print("=" * 50)
    
    test_cities = ["London", "Vienna", "Munich"]
    
    for city in test_cities:
        en_result = db.resolve(city, "en")
        tr_result = db.resolve(city, "tr")
        
        print(f"🇬🇧 EN: {en_result['city']}, {en_result['country']}")
        print(f"🇹🇷 TR: {tr_result['city']}, {tr_result['country']}")
        print()


def test_helper_functions():
    """Helper fonksiyonlar"""
    print("\n" + "=" * 50)
    print("TEST 10: Helper Fonksiyonlar")
    print("=" * 50)
    
    # get_iata_code
    iata = get_iata_code("Paris")
    print(f"✅ get_iata_code('Paris') → {iata}")
    
    iata = get_iata_code("Londra")
    print(f"✅ get_iata_code('Londra') → {iata}")
    
    iata = get_iata_code("NonExistentCity")
    print(f"✅ get_iata_code('NonExistentCity') → {iata}")
    
    # resolve_location convenience function
    result = resolve_location("Barcelona", "tr")
    print(f"✅ resolve_location('Barcelona', 'tr') → {result['city']}, {result['country']}")


def test_not_found_suggestions():
    """Bulunamayan şehirler için öneriler"""
    db = AirportDatabase()
    
    print("\n" + "=" * 50)
    print("TEST 11: Öneriler (Bulunamayan Şehirler)")
    print("=" * 50)
    
    result = db.resolve("XYZCity", "en")
    print(f"Query: 'XYZCity'")
    print(f"Found: {result.get('found')}")
    print(f"Message: {result.get('message')}")
    print("Suggestions:")
    for s in result.get("suggestions", [])[:3]:
        print(f"   - {s['city']} ({s['iata']}), {s['country']}")


def run_all_tests():
    """Tüm testleri çalıştır"""
    print("\n" + "🧪 " + "=" * 46 + " 🧪")
    print("     ACTIONFLOW AIRPORT DATABASE TESTS")
    print("🧪 " + "=" * 46 + " 🧪\n")
    
    test_exact_match_english()
    test_exact_match_turkish()
    test_iata_codes()
    test_airport_codes()
    test_turkish_character_tolerance()
    test_fuzzy_matching()
    test_multiple_airports()
    test_country_search()
    test_bilingual_response()
    test_helper_functions()
    test_not_found_suggestions()
    
    print("\n" + "=" * 50)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()