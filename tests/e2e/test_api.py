"""
ActionFlow AI - FastAPI Endpoint Test Suite
Tests all API endpoints to verify they work correctly.

Usage:
    1. Start the API: uvicorn app.main:app --port 8000
    2. Run this test: python test_api.py

Supports both:
    - Live API testing (default): Requires running server
    - Pytest mode: Use pytest tests/integration/test_api.py
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

# Data collected during tests
collected_data = {
    "hotel_ids": [],
    "booking_dest_id": None,
    "flight_offer": None,
    "priced_offer": None,
    "flight_order_id": None,
    "offer_id": None,
}


def test(
    name: str,
    method: str,
    endpoint: str,
    params: dict = None,
    json_data: dict = None,
    expected_field: str = None,
    expected_status: int = None
):
    """
    Run a single API test.
    
    Args:
        name: Test name for display
        method: HTTP method (GET, POST, DELETE)
        endpoint: API endpoint path
        params: Query parameters
        json_data: JSON body for POST requests
        expected_field: Field that should exist in response
        expected_status: Expected HTTP status code (if None, accepts < 400)
    
    Returns:
        tuple: (success: bool, data: dict)
    """
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
        
        # Determine success
        if expected_status:
            success = response.status_code == expected_status
        else:
            success = response.status_code < 400
        
        # Parse response
        try:
            data = response.json() if response.text else {}
        except json.JSONDecodeError:
            data = {"raw": response.text[:200]}
        
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
            "count": count,
            "endpoint": endpoint
        })
        
        icon = "✅" if success else "❌"
        count_str = f"({count} results)" if count is not None else ""
        status_str = f"[{response.status_code}]" if not success else ""
        print(f"   {icon} {name:45} {count_str} {status_str}")
        
        return success, data
        
    except requests.exceptions.ConnectionError:
        print(f"   ❌ {name:45} CONNECTION ERROR - Is the API running?")
        results.append({"name": name, "success": False, "status": "CONNECTION_ERROR", "endpoint": endpoint})
        return False, None
    except requests.exceptions.Timeout:
        print(f"   ❌ {name:45} TIMEOUT")
        results.append({"name": name, "success": False, "status": "TIMEOUT", "endpoint": endpoint})
        return False, None
    except Exception as e:
        print(f"   ❌ {name:45} ERROR: {str(e)[:50]}")
        results.append({"name": name, "success": False, "status": "ERROR", "error": str(e), "endpoint": endpoint})
        return False, None


def test_health_endpoints():
    """Test health and info endpoints"""
    print("\n📍 HEALTH CHECK")
    print("-" * 70)
    
    test("Root Endpoint", "GET", "/", expected_field="name")
    test("Health Check", "GET", "/health", expected_field="status")
    test("Database Stats", "GET", "/stats", expected_field="users")


def test_amadeus_hotel_endpoints():
    """Test Amadeus-based hotel endpoints"""
    print("\n🏨 HOTEL ENDPOINTS (Amadeus)")
    print("-" * 70)
    
    # Search by city
    cities = ["PAR", "IST", "AMS"]
    for city in cities:
        success, data = test(
            f"Hotel Search - {city}",
            "GET",
            f"/hotels/search/city/{city}",
            params={"radius": 5},
            expected_field="hotels"
        )
        if success and data and not collected_data["hotel_ids"]:
            hotels = data.get("hotels", [])[:3]
            collected_data["hotel_ids"] = [h.get("hotelId") for h in hotels if h.get("hotelId")]
    
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
    if collected_data["hotel_ids"]:
        success, data = test(
            "Hotel Offers - Pricing",
            "POST",
            "/hotels/offers",
            json_data={
                "hotel_ids": collected_data["hotel_ids"],
                "check_in": CHECK_IN,
                "check_out": CHECK_OUT,
                "adults": 1,
                "rooms": 1,
                "currency": "EUR"
            },
            expected_field="offers"
        )
        
        if success and data:
            offers = data.get("offers", [])
            if offers and offers[0].get("offers"):
                offer_id = offers[0]["offers"][0].get("id")
                if offer_id:
                    collected_data["offer_id"] = offer_id
                    print(f"      📋 Offer ID: {offer_id[:30]}...")


def test_booking_hotel_endpoints():
    """Test Booking.com-based hotel endpoints (via accommodation_routes)"""
    print("\n🏨 HOTEL ENDPOINTS (Booking.com API)")
    print("-" * 70)
    
    # Search destination
    success, data = test(
        "Hotel Destination - London",
        "GET",
        "/api/v1/hotels/search-destination",
        params={"city_name": "London"},
        expected_field="dest_id"
    )
    
    if success and data:
        collected_data["booking_dest_id"] = data.get("dest_id")
        print(f"      📍 Dest ID: {data.get('dest_id')}")
    
    # Search hotels with destination ID
    if collected_data["booking_dest_id"]:
        test(
            "Hotel Search - Booking.com",
            "GET",
            "/api/v1/hotels/search",
            params={
                "dest_id": collected_data["booking_dest_id"],
                "arrival_date": CHECK_IN,
                "departure_date": CHECK_OUT,
                "adults": 1
            }
        )
    
    # Hotel policies (using a sample hotel ID)
    test(
        "Hotel Policies - Sample",
        "GET",
        "/api/v1/hotels/123456/policies"
    )
    
    # Hotel description
    test(
        "Hotel Description - Sample",
        "GET",
        "/api/v1/hotels/123456/description"
    )


def test_amadeus_flight_endpoints():
    """Test Amadeus-based flight endpoints"""
    print("\n✈️ FLIGHT ENDPOINTS (Amadeus)")
    print("-" * 70)
    
    # Search flights
    routes = [("PAR", "LON"), ("IST", "AMS")]
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
        if success and data and not collected_data["flight_offer"]:
            flights = data.get("flights", [])
            if flights:
                collected_data["flight_offer"] = flights[0]
                price = flights[0].get("price", {})
                print(f"      💰 Cheapest: {price.get('total', '?')} {price.get('currency', 'EUR')}")
    
    # Price verification
    if collected_data["flight_offer"]:
        success, data = test(
            "Flight Price - Verify",
            "POST",
            "/flights/price",
            json_data=collected_data["flight_offer"],
            expected_field="offer"
        )
        
        if success and data:
            collected_data["priced_offer"] = data.get("offer")
            price = data.get("price", {})
            print(f"      💰 Confirmed: {price.get('grandTotal', price.get('total', '?'))} {price.get('currency', 'EUR')}")
    
    # Flight booking (only if we have priced offer)
    if collected_data["priced_offer"]:
        success, data = test(
            "Flight Booking - Create",
            "POST",
            "/flights/book",
            json_data={
                "flight_offer": collected_data["priced_offer"],
                "first_name": "TEST",
                "last_name": "USER",
                "date_of_birth": "1990-01-15",
                "gender": "MALE",
                "email": "test@actionflow.ai",
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
            collected_data["flight_order_id"] = data.get("booking_id")
            pnr = data.get("pnr")
            if pnr:
                print(f"      📋 PNR: {pnr}")
    
    # Get flight order
    if collected_data["flight_order_id"]:
        test(
            "Flight Order - Get Details",
            "GET",
            f"/flights/orders/{collected_data['flight_order_id']}",
            expected_field="data"
        )


def test_advanced_flight_endpoints():
    """Test advanced flight endpoints (via flight_routes router)"""
    print("\n✈️ FLIGHT ENDPOINTS (Advanced - Router)")
    print("-" * 70)
    
    # These endpoints require a valid offer_id from cache
    # Using a dummy ID to test endpoint availability
    dummy_offer_id = "TEST_OFFER_123"
    
    # Price by offer ID
    test(
        "Flight Price by Offer ID",
        "POST",
        f"/api/v1/flights/price/{dummy_offer_id}",
        expected_status=410  # Expected: offer expired
    )
    
    # Seatmap
    test(
        "Flight Seatmap",
        "GET",
        f"/api/v1/flights/{dummy_offer_id}/seatmap",
        expected_status=410  # Expected: offer expired
    )
    
    # Ancillaries
    test(
        "Flight Ancillaries",
        "GET",
        f"/api/v1/flights/{dummy_offer_id}/ancillaries",
        expected_status=410  # Expected: offer expired
    )


def test_activity_endpoints():
    """Test activity endpoints"""
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


def test_utility_endpoints():
    """Test utility endpoints"""
    print("\n🔧 UTILITY ENDPOINTS")
    print("-" * 70)
    
    # Location search
    locations = ["Istanbul", "Paris", "Amsterdam"]
    for loc in locations:
        test(
            f"Location Search - {loc}",
            "GET",
            "/locations/search",
            params={"keyword": loc},
            expected_field="locations"
        )
    
    # Airline check-in links
    airlines = ["TK", "KL", "AF"]
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
        "Travel Recommendations",
        "GET",
        "/recommendations",
        params={"cities": "PAR", "country": "FR"},
        expected_field="recommendations"
    )


def test_policy_endpoints():
    """Test policy (RAG) endpoints"""
    print("\n📜 POLICY ENDPOINTS (RAG)")
    print("-" * 70)
    
    test(
        "List Policies",
        "GET",
        "/policies",
        expected_field="policies"
    )
    
    test(
        "Search Policies - cancellation",
        "GET",
        "/policies/search/cancellation",
        expected_field="results"
    )


def test_chat_endpoint():
    """Test AI agent chat endpoint"""
    print("\n🤖 CHAT ENDPOINT (AI Agent)")
    print("-" * 70)
    
    test(
        "Chat - Simple Query",
        "POST",
        "/chat",
        json_data={
            "message": "Hello, I need help with my booking",
            "user_id": "test_user_123"
        },
        expected_field="conversation_id"
    )


def print_summary():
    """Print test summary"""
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for r in results if r.get("success"))
    failed = total - passed
    
    # Group by category
    categories = {
        "Health": [],
        "Hotel (Amadeus)": [],
        "Hotel (Booking)": [],
        "Flight (Amadeus)": [],
        "Flight (Advanced)": [],
        "Activity": [],
        "Policy": [],
        "Chat": [],
        "Utility": []
    }
    
    for r in results:
        name = r["name"]
        endpoint = r.get("endpoint", "")
        
        if "Health" in name or "Root" in name or "Stats" in name:
            categories["Health"].append(r)
        elif "/api/v1/hotels" in endpoint:
            categories["Hotel (Booking)"].append(r)
        elif "Hotel" in name:
            categories["Hotel (Amadeus)"].append(r)
        elif "/api/v1/flights" in endpoint:
            categories["Flight (Advanced)"].append(r)
        elif "Flight" in name:
            categories["Flight (Amadeus)"].append(r)
        elif "Activit" in name:
            categories["Activity"].append(r)
        elif "Polic" in name:
            categories["Policy"].append(r)
        elif "Chat" in name:
            categories["Chat"].append(r)
        else:
            categories["Utility"].append(r)
    
    print(f"""
┌──────────────────────────────────────────────────────────────────────┐
│  Category              Tests    Passed    Failed    Rate             │
├──────────────────────────────────────────────────────────────────────┤""")
    
    for cat, items in categories.items():
        if items:
            t = len(items)
            p = sum(1 for i in items if i.get("success"))
            f = t - p
            rate = (p / t) * 100 if t > 0 else 0
            status = "✅" if rate >= 70 else "⚠️" if rate >= 30 else "❌"
            print(f"│  {cat:20}   {t:4}      {p:4}      {f:4}     {rate:5.1f}% {status}  │")
    
    print(f"""├──────────────────────────────────────────────────────────────────────┤
│  TOTAL                  {total:4}      {passed:4}      {failed:4}     {(passed/total)*100 if total > 0 else 0:5.1f}%      │
└──────────────────────────────────────────────────────────────────────┘
    """)
    
    # Failed tests
    failed_tests = [r for r in results if not r.get("success")]
    if failed_tests:
        print("\n⚠️ FAILED TESTS:")
        for r in failed_tests:
            print(f"   • {r['name']}: {r.get('status', 'Unknown')} - {r.get('endpoint', '')}")
    
    # Overall result
    print("\n" + "=" * 70)
    if total == 0:
        print("⚠️ NO TESTS RUN - Check API connection")
    elif passed == total:
        print("🎉 ALL TESTS PASSED! API is fully operational.")
    elif passed / total >= 0.8:
        print("✅ MOSTLY WORKING - Some endpoints may have test environment limitations.")
    elif passed / total >= 0.5:
        print("⚠️ PARTIAL SUCCESS - Check failed endpoints.")
    else:
        print("❌ MULTIPLE FAILURES - Check API configuration and credentials.")
    print("=" * 70)
    
    # Save results
    with open("test_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "passed": passed,
            "failed": failed,
            "results": results
        }, f, indent=2)
    print("\n📁 Results saved to: test_results.json")


def main():
    """Main test runner"""
    print("=" * 70)
    print("ACTIONFLOW AI - FASTAPI ENDPOINT TEST")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Date: {TODAY.strftime('%Y-%m-%d %H:%M')}")
    print(f"Flight Date: {FLIGHT_DATE}")
    print(f"Hotel Dates: {CHECK_IN} → {CHECK_OUT}")
    print("=" * 70)
    
    # Run all test groups
    test_health_endpoints()
    test_amadeus_hotel_endpoints()
    test_booking_hotel_endpoints()
    test_amadeus_flight_endpoints()
    test_advanced_flight_endpoints()
    test_activity_endpoints()
    test_utility_endpoints()
    test_policy_endpoints()
    test_chat_endpoint()
    
    # Print summary
    print_summary()


if __name__ == "__main__":
    print("\n⚠️  Make sure the API is running on http://localhost:8000")
    print("    Start it with: cd backend && uvicorn app.main:app --port 8000\n")
    
    user_input = input("Press Enter to start tests (or 'q' to quit)... ")
    if user_input.lower() != 'q':
        print()
        main()