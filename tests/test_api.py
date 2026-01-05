"""
ActionFlow AI - FastAPI Endpoint Test Suite
Tests all API endpoints to verify they work correctly.

Usage:
    1. Start the API: uvicorn main:app --port 8000
    2. Run this test: python test_api.py
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"

# Test dates
TODAY = datetime.now()
CHECK_IN = (TODAY + timedelta(days=30)).strftime("%Y-%m-%d")
CHECK_OUT = (TODAY + timedelta(days=32)).strftime("%Y-%m-%d")
FLIGHT_DATE = (TODAY + timedelta(days=30)).strftime("%Y-%m-%d")

# Test results storage
results = []
hotel_ids = []
flight_offer = None
priced_offer = None
flight_order_id = None


def test(name: str, method: str, endpoint: str, params: dict = None, json_data: dict = None, expected_field: str = None):
    """Run a single test"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=json_data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, timeout=30)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        success = response.status_code < 400
        data = response.json() if response.text else {}
        
        # Check expected field exists
        if success and expected_field:
            if expected_field not in data:
                success = False
        
        # Get count if available
        count = data.get("count", len(data) if isinstance(data, list) else None)
        
        results.append({
            "name": name,
            "success": success,
            "status": response.status_code,
            "count": count
        })
        
        icon = "✅" if success else "❌"
        count_str = f"({count} results)" if count is not None else ""
        print(f"   {icon} {name:45} {count_str}")
        
        return success, data
        
    except requests.exceptions.ConnectionError:
        print(f"   ❌ {name:45} CONNECTION ERROR - Is the API running?")
        results.append({"name": name, "success": False, "status": "CONNECTION_ERROR"})
        return False, None
    except Exception as e:
        print(f"   ❌ {name:45} ERROR: {str(e)[:50]}")
        results.append({"name": name, "success": False, "status": "ERROR", "error": str(e)})
        return False, None


def main():
    global hotel_ids, flight_offer, priced_offer, flight_order_id
    
    print("=" * 70)
    print("ACTIONFLOW AI - FASTAPI ENDPOINT TEST")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Date: {TODAY.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # ═══════════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════════════
    print("\n📍 HEALTH CHECK")
    print("-" * 70)
    
    test("Root Endpoint", "GET", "/", expected_field="name")
    test("Health Check", "GET", "/health", expected_field="status")
    
    # ═══════════════════════════════════════════════════════════════════
    # HOTEL TESTS
    # ═══════════════════════════════════════════════════════════════════
    print("\n🏨 HOTEL ENDPOINTS")
    print("-" * 70)
    
    # Search by city
    cities = ["PAR", "IST", "AMS", "LON"]
    for city in cities:
        success, data = test(
            f"Hotel Search - {city}",
            "GET",
            f"/hotels/search/city/{city}",
            params={"radius": 5},
            expected_field="hotels"
        )
        if success and data and not hotel_ids:
            hotels = data.get("hotels", [])[:3]
            hotel_ids = [h.get("hotelId") for h in hotels if h.get("hotelId")]
    
    # Search by location (Schiphol Airport)
    test(
        "Hotel Search - By Location (Schiphol)",
        "GET",
        "/hotels/search/location",
        params={"lat": 52.3105, "lng": 4.7683, "radius": 5},
        expected_field="hotels"
    )
    
    # Hotel autocomplete
    test(
        "Hotel Autocomplete - Hilton",
        "GET",
        "/hotels/autocomplete",
        params={"keyword": "HILTON"},
        expected_field="hotels"
    )
    
    # Hotel offers (if we have hotel IDs)
    if hotel_ids:
        success, data = test(
            "Hotel Offers - Pricing",
            "POST",
            "/hotels/offers",
            json_data={
                "hotel_ids": hotel_ids,
                "check_in": CHECK_IN,
                "check_out": CHECK_OUT,
                "adults": 1,
                "rooms": 1,
                "currency": "EUR"
            },
            expected_field="offers"
        )
        
        # Get offer ID for booking test
        if success and data:
            offers = data.get("offers", [])
            if offers and offers[0].get("offers"):
                offer_id = offers[0]["offers"][0].get("id")
                if offer_id:
                    print(f"      📋 Offer ID: {offer_id[:20]}...")
    
    # ═══════════════════════════════════════════════════════════════════
    # FLIGHT TESTS
    # ═══════════════════════════════════════════════════════════════════
    print("\n✈️ FLIGHT ENDPOINTS")
    print("-" * 70)
    
    # Search flights
    routes = [("PAR", "LON"), ("IST", "AMS"), ("NYC", "LAX")]
    for origin, dest in routes:
        success, data = test(
            f"Flight Search - {origin}→{dest}",
            "GET",
            "/flights/search",
            params={
                "origin": origin,
                "destination": dest,
                "date": FLIGHT_DATE,
                "adults": 1,
                "max_results": 5
            },
            expected_field="flights"
        )
        
        # Store first flight offer
        if success and data and not flight_offer:
            flights = data.get("flights", [])
            if flights:
                flight_offer = flights[0]
                price = flight_offer.get("price", {})
                print(f"      💰 Cheapest: {price.get('total', '?')} {price.get('currency', 'EUR')}")
    
    # Price verification
    if flight_offer:
        success, data = test(
            "Flight Price - Verify",
            "POST",
            "/flights/price",
            json_data=flight_offer,
            expected_field="offer"
        )
        
        if success and data:
            priced_offer = data.get("offer")
            price = data.get("price", {})
            print(f"      💰 Confirmed: {price.get('grandTotal', price.get('total', '?'))} {price.get('currency', 'EUR')}")
    
    # Flight booking
    if priced_offer:
        success, data = test(
            "Flight Booking - Create",
            "POST",
            "/flights/book",
            json_data={
                "flight_offer": priced_offer,
                "first_name": "TEST",
                "last_name": "USER",
                "date_of_birth": "1990-01-15",
                "gender": "MALE",
                "email": "test@example.com",
                "phone": "612345678",
                "passport_number": "AB1234567",
                "passport_expiry": "2030-01-01",
                "nationality": "FR",
                "address_line": "123 Test Street",
                "postal_code": "75001",
                "city": "Paris",
                "country": "FR"
            }
        )
        
        if success and data:
            flight_order_id = data.get("booking_id")
            pnr = data.get("pnr")
            if pnr:
                print(f"      📋 PNR: {pnr}")
            if flight_order_id:
                print(f"      📋 Order ID: {flight_order_id[:30]}...")
    
    # Get flight order
    if flight_order_id:
        test(
            "Flight Order - Get Details",
            "GET",
            f"/flights/orders/{flight_order_id}",
            expected_field="data"
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # ACTIVITY TESTS
    # ═══════════════════════════════════════════════════════════════════
    print("\n🎭 ACTIVITY ENDPOINTS")
    print("-" * 70)
    
    # By coordinates
    test(
        "Activities - Paris (coordinates)",
        "GET",
        "/activities/search",
        params={"lat": 48.8566, "lng": 2.3522, "radius": 5},
        expected_field="activities"
    )
    
    # By city code
    cities = ["PAR", "IST", "BCN"]
    for city in cities:
        test(
            f"Activities - {city} (city code)",
            "GET",
            f"/activities/city/{city}",
            params={"radius": 10},
            expected_field="activities"
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # UTILITY TESTS
    # ═══════════════════════════════════════════════════════════════════
    print("\n🔧 UTILITY ENDPOINTS")
    print("-" * 70)
    
    # Location search
    locations = ["Istanbul", "Paris", "London", "Amsterdam"]
    for loc in locations:
        test(
            f"Location Search - {loc}",
            "GET",
            "/locations/search",
            params={"keyword": loc},
            expected_field="locations"
        )
    
    # Airline check-in links
    airlines = ["TK", "KL", "AF", "LH"]
    for airline in airlines:
        test(
            f"Check-in Link - {airline}",
            "GET",
            f"/airlines/{airline}/checkin",
            expected_field="links"
        )
    
    # Airline info
    test(
        "Airline Info - TK",
        "GET",
        "/airlines/TK",
        expected_field="iataCode"
    )
    
    # Recommendations
    test(
        "Travel Recommendations - PAR",
        "GET",
        "/recommendations",
        params={"cities": "PAR", "country": "FR"},
        expected_field="recommendations"
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for r in results if r.get("success"))
    failed = total - passed
    
    # Group by category
    categories = {
        "Health": [],
        "Hotel": [],
        "Flight": [],
        "Activity": [],
        "Utility": []
    }
    
    for r in results:
        name = r["name"]
        if "Health" in name or "Root" in name:
            categories["Health"].append(r)
        elif "Hotel" in name:
            categories["Hotel"].append(r)
        elif "Flight" in name:
            categories["Flight"].append(r)
        elif "Activit" in name:
            categories["Activity"].append(r)
        else:
            categories["Utility"].append(r)
    
    print(f"""
    ┌────────────────────────────────────────────────────────────────────┐
    │  Category          Tests    Passed    Failed    Rate              │
    ├────────────────────────────────────────────────────────────────────┤""")
    
    for cat, items in categories.items():
        if items:
            t = len(items)
            p = sum(1 for i in items if i.get("success"))
            f = t - p
            rate = (p / t) * 100 if t > 0 else 0
            status = "✅" if rate >= 70 else "⚠️" if rate >= 30 else "❌"
            print(f"    │  {cat:16}   {t:4}      {p:4}      {f:4}     {rate:5.1f}% {status}   │")
    
    print(f"""    ├────────────────────────────────────────────────────────────────────┤
    │  TOTAL             {total:4}      {passed:4}      {failed:4}     {(passed/total)*100:5.1f}%       │
    └────────────────────────────────────────────────────────────────────┘
    """)
    
    # Failed tests
    failed_tests = [r for r in results if not r.get("success")]
    if failed_tests:
        print("\n⚠️ FAILED TESTS:")
        for r in failed_tests:
            print(f"   • {r['name']}: {r.get('status', 'Unknown')}")
    
    # Overall result
    print("\n" + "=" * 70)
    if passed == total:
        print("🎉 ALL TESTS PASSED! API is fully operational.")
    elif passed / total >= 0.8:
        print("✅ MOSTLY WORKING - Some endpoints may have test environment limitations.")
    elif passed / total >= 0.5:
        print("⚠️ PARTIAL SUCCESS - Check failed endpoints.")
    else:
        print("❌ MULTIPLE FAILURES - Check API configuration and Amadeus credentials.")
    print("=" * 70)
    
    # Save results
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n📁 Results saved to: test_results.json")


if __name__ == "__main__":
    print("\n⚠️  Make sure the API is running on http://localhost:8000")
    print("    Start it with: uvicorn main:app --port 8000\n")
    
    input("Press Enter to start tests...")
    print()
    
    main()