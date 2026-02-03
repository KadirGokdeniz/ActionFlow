"""
ActionFlow MCP Tools - Booking Operations
Rezervasyon oluşturma, görüntüleme, iptal ve değişiklik işlemleri

Tools:
- create_booking: Yeni rezervasyon oluştur (flight, hotel, package)
- get_user_bookings: Kullanıcının rezervasyonlarını listele
- get_booking_details: Tek rezervasyon detayı
- cancel_booking: Rezervasyon iptali
- modify_booking: Rezervasyon değişikliği
"""

from typing import Optional, List, Dict, Any
import httpx


# ═══════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS (MCP Schema)
# ═══════════════════════════════════════════════════════════════════

CREATE_BOOKING_DEFINITION = {
    "name": "create_booking",
    "description": """Yeni bir rezervasyon oluşturur. Uçuş, otel veya paket (uçuş+otel) rezervasyonu yapabilir.
    
DİKKAT: Bu işlem GERÇEK bir rezervasyon oluşturur! Kullanıcıdan ONAY aldıktan sonra çağırın.

Booking types:
- flight: Sadece uçuş
- hotel: Sadece otel  
- package: Uçuş + Otel birlikte (önerilen)""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "booking_type": {
                "type": "string",
                "description": "Rezervasyon tipi: flight, hotel veya package",
                "enum": ["flight", "hotel", "package"]
            },
            "flight_offer_id": {
                "type": "string",
                "description": "Uçuş offer ID (flight veya package için gerekli)"
            },
            "hotel_offer_id": {
                "type": "string",
                "description": "Otel offer ID (hotel veya package için gerekli)"
            },
            "passenger_first_name": {
                "type": "string",
                "description": "Yolcu adı"
            },
            "passenger_last_name": {
                "type": "string",
                "description": "Yolcu soyadı"
            },
            "passenger_email": {
                "type": "string",
                "description": "İletişim email adresi"
            },
            "passenger_phone": {
                "type": "string",
                "description": "İletişim telefon numarası (opsiyonel)"
            },
            "check_in": {
                "type": "string",
                "description": "Giriş tarihi (YYYY-MM-DD) - hotel ve package için"
            },
            "check_out": {
                "type": "string",
                "description": "Çıkış tarihi (YYYY-MM-DD) - hotel ve package için"
            },
            "guests": {
                "type": "integer",
                "description": "Misafir sayısı (varsayılan: 1)",
                "default": 1
            }
        },
        "required": ["booking_type", "passenger_first_name", "passenger_last_name", "passenger_email"]
    }
}

GET_USER_BOOKINGS_DEFINITION = {
    "name": "get_user_bookings",
    "description": "Kullanıcının mevcut rezervasyonlarını listeler. Aktif, geçmiş ve iptal edilmiş tüm rezervasyonları gösterir.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "Kullanıcı ID"
            },
            "status": {
                "type": "string",
                "description": "Rezervasyon durumu filtresi",
                "enum": ["pending", "confirmed", "cancelled", "all"],
                "default": "all"
            },
            "booking_type": {
                "type": "string",
                "description": "Rezervasyon tipi filtresi",
                "enum": ["flight", "hotel", "package", "all"],
                "default": "all"
            }
        },
        "required": ["user_id"]
    }
}

CANCEL_BOOKING_DEFINITION = {
    "name": "cancel_booking",
    "description": """Bir rezervasyonu iptal eder. 

DİKKAT: Bu işlem GERİ ALINAMAZ! Kullanıcıdan ONAY aldıktan sonra çağırın.
İptal politikasına göre ücret kesintisi olabilir.""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "booking_id": {
                "type": "string",
                "description": "İptal edilecek rezervasyon ID"
            },
            "reason": {
                "type": "string",
                "description": "İptal nedeni (opsiyonel)"
            }
        },
        "required": ["booking_id"]
    }
}

GET_BOOKING_DETAILS_DEFINITION = {
    "name": "get_booking_details",
    "description": "Tek bir rezervasyonun detaylı bilgilerini getirir: uçuş/otel detayları, fiyat, durum vb.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "booking_id": {
                "type": "string",
                "description": "Rezervasyon ID veya PNR"
            }
        },
        "required": ["booking_id"]
    }
}

MODIFY_BOOKING_DEFINITION = {
    "name": "modify_booking",
    "description": """Mevcut bir rezervasyonda değişiklik yapar (tarih değişikliği vb).

DİKKAT: Değişiklik ücreti uygulanabilir. Kullanıcıya bilgi verdikten sonra çağırın.""",
    "inputSchema": {
        "type": "object",
        "properties": {
            "booking_id": {
                "type": "string",
                "description": "Değiştirilecek rezervasyon ID"
            },
            "new_check_in": {
                "type": "string",
                "description": "Yeni giriş/kalkış tarihi (YYYY-MM-DD)"
            },
            "new_check_out": {
                "type": "string",
                "description": "Yeni çıkış/dönüş tarihi (YYYY-MM-DD)"
            }
        },
        "required": ["booking_id"]
    }
}

# Export için liste
TOOL_DEFINITIONS = [
    CREATE_BOOKING_DEFINITION,
    GET_USER_BOOKINGS_DEFINITION,
    CANCEL_BOOKING_DEFINITION,
    GET_BOOKING_DETAILS_DEFINITION,
    MODIFY_BOOKING_DEFINITION
]


# ═══════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════

async def create_booking(
    booking_type: str,
    passenger_first_name: str,
    passenger_last_name: str,
    passenger_email: str,
    passenger_phone: Optional[str] = None,
    flight_offer_id: Optional[str] = None,
    hotel_offer_id: Optional[str] = None,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
    guests: int = 1,
    http_client: httpx.AsyncClient = None
) -> dict:
    """
    Yeni rezervasyon oluşturur
    
    Args:
        booking_type: flight, hotel, veya package
        passenger_*: Yolcu bilgileri
        flight_offer_id: Uçuş teklif ID
        hotel_offer_id: Otel teklif ID
        check_in/check_out: Tarihler
        guests: Misafir sayısı
        http_client: HTTP client
    
    Returns:
        Rezervasyon detayları veya hata
    """
    if http_client is None:
        return {"success": False, "error": "HTTP client not provided"}
    
    try:
        # Prepare passenger info
        passenger = {
            "first_name": passenger_first_name,
            "last_name": passenger_last_name,
            "email": passenger_email,
            "phone": passenger_phone
        }
        
        # Route to appropriate endpoint based on booking type
        if booking_type == "flight":
            if not flight_offer_id:
                return {"success": False, "error": "flight_offer_id is required for flight booking"}
            
            response = await http_client.post(
                "/api/v1/bookings/flight",
                json={
                    "offer_id": flight_offer_id,
                    "passengers": [passenger],
                    "contact_email": passenger_email,
                    "contact_phone": passenger_phone
                }
            )
        
        elif booking_type == "hotel":
            if not hotel_offer_id:
                return {"success": False, "error": "hotel_offer_id is required for hotel booking"}
            if not check_in or not check_out:
                return {"success": False, "error": "check_in and check_out dates are required for hotel booking"}
            
            response = await http_client.post(
                "/api/v1/bookings/hotel",
                json={
                    "offer_id": hotel_offer_id,
                    "guest_name": f"{passenger_first_name} {passenger_last_name}",
                    "check_in": check_in,
                    "check_out": check_out,
                    "guests": guests,
                    "contact_email": passenger_email
                }
            )
        
        elif booking_type == "package":
            if not flight_offer_id or not hotel_offer_id:
                return {"success": False, "error": "Both flight_offer_id and hotel_offer_id are required for package booking"}
            if not check_in or not check_out:
                return {"success": False, "error": "check_in and check_out dates are required for package booking"}
            
            response = await http_client.post(
                "/api/v1/bookings/package",
                json={
                    "flight_offer_id": flight_offer_id,
                    "hotel_offer_id": hotel_offer_id,
                    "passengers": [passenger],
                    "check_in": check_in,
                    "check_out": check_out,
                    "contact_email": passenger_email,
                    "contact_phone": passenger_phone
                }
            )
        
        else:
            return {"success": False, "error": f"Invalid booking type: {booking_type}"}
        
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "booking_id": data.get("booking_id"),
            "pnr": data.get("pnr"),
            "status": data.get("status"),
            "booking_type": booking_type,
            "total_amount": data.get("total_amount"),
            "currency": data.get("currency", "EUR"),
            "message": data.get("message"),
            "details": data.get("details"),
            "confirmation": f"✅ Booking confirmed! PNR: {data.get('pnr')}. Confirmation email will be sent to {passenger_email}."
        }
        
    except httpx.HTTPStatusError as e:
        error_detail = "Unknown error"
        try:
            error_detail = e.response.json().get("detail", str(e))
        except:
            error_detail = str(e)
        return {
            "success": False,
            "error": f"Booking failed: {error_detail}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Booking error: {str(e)}"
        }


async def get_user_bookings(
    user_id: str,
    status: str = "all",
    booking_type: str = "all",
    http_client: httpx.AsyncClient = None
) -> dict:
    """Kullanıcının rezervasyonlarını listeler"""
    if http_client is None:
        return {"success": False, "error": "HTTP client not provided"}
    
    try:
        params = {}
        if status != "all":
            params["status"] = status
        if booking_type != "all":
            params["type"] = booking_type
        
        response = await http_client.get(
            f"/api/v1/bookings/user/{user_id}",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        bookings = data.get("bookings", [])
        
        formatted_bookings = []
        for b in bookings:
            booking_info = {
                "id": b.get("id"),
                "pnr": b.get("pnr"),
                "type": b.get("booking_type"),
                "status": b.get("status"),
                "total_amount": b.get("total_amount"),
                "currency": b.get("currency", "EUR"),
                "created_at": b.get("created_at"),
            }
            
            details = b.get("details", {})
            if b.get("booking_type") == "flight":
                booking_info["route"] = details.get("route")
                booking_info["departure_date"] = details.get("departure_date")
            elif b.get("booking_type") == "hotel":
                booking_info["hotel_name"] = details.get("hotel_name")
                booking_info["check_in"] = details.get("check_in")
                booking_info["check_out"] = details.get("check_out")
            elif b.get("booking_type") == "package":
                flight = details.get("flight", {})
                hotel = details.get("hotel", {})
                booking_info["route"] = flight.get("route")
                booking_info["hotel_name"] = hotel.get("name")
                booking_info["dates"] = f"{hotel.get('check_in')} to {hotel.get('check_out')}"
            
            formatted_bookings.append(booking_info)
        
        return {
            "success": True,
            "user_id": user_id,
            "count": len(formatted_bookings),
            "bookings": formatted_bookings
        }
        
    except httpx.HTTPStatusError as e:
        return {"success": False, "error": f"API error: {e.response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def cancel_booking(
    booking_id: str,
    reason: Optional[str] = None,
    http_client: httpx.AsyncClient = None
) -> dict:
    """Rezervasyonu iptal eder"""
    if http_client is None:
        return {"success": False, "error": "HTTP client not provided"}
    
    try:
        response = await http_client.post(
            f"/api/v1/bookings/{booking_id}/cancel",
            json={"reason": reason} if reason else {}
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "booking_id": booking_id,
            "status": "cancelled",
            "refund_amount": data.get("refund_amount"),
            "currency": data.get("currency", "EUR"),
            "refund_status": data.get("refund_status", "processing"),
            "message": data.get("message"),
            "policy_applied": data.get("policy_applied")
        }
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"success": False, "error": f"Booking not found: {booking_id}"}
        elif e.response.status_code == 400:
            try:
                error_detail = e.response.json().get("detail", "Cannot cancel")
            except:
                error_detail = "Cannot cancel this booking"
            return {"success": False, "error": error_detail}
        return {"success": False, "error": f"API error: {e.response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_booking_details(
    booking_id: str,
    http_client: httpx.AsyncClient = None
) -> dict:
    """Rezervasyon detaylarını getirir"""
    if http_client is None:
        return {"success": False, "error": "HTTP client not provided"}
    
    try:
        response = await http_client.get(f"/api/v1/bookings/{booking_id}")
        response.raise_for_status()
        data = response.json()
        
        booking = data.get("booking", data)
        
        return {
            "success": True,
            "booking": {
                "id": booking.get("id"),
                "pnr": booking.get("pnr"),
                "type": booking.get("booking_type"),
                "status": booking.get("status"),
                "total_amount": booking.get("total_amount"),
                "currency": booking.get("currency", "EUR"),
                "created_at": booking.get("created_at"),
                "details": booking.get("details", {})
            }
        }
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"success": False, "error": f"Booking not found: {booking_id}"}
        return {"success": False, "error": f"API error: {e.response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def modify_booking(
    booking_id: str,
    new_check_in: Optional[str] = None,
    new_check_out: Optional[str] = None,
    http_client: httpx.AsyncClient = None
) -> dict:
    """Rezervasyonda değişiklik yapar"""
    if http_client is None:
        return {"success": False, "error": "HTTP client not provided"}
    
    if not new_check_in and not new_check_out:
        return {"success": False, "error": "At least one modification (new_check_in or new_check_out) is required"}
    
    try:
        modification = {}
        if new_check_in:
            modification["check_in"] = new_check_in
        if new_check_out:
            modification["check_out"] = new_check_out
        
        response = await http_client.post(
            f"/api/v1/bookings/{booking_id}/modify",
            json=modification
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "booking_id": booking_id,
            "message": data.get("message"),
            "updated_details": data.get("updated_details"),
            "modification_fee": data.get("modification_fee", 0)
        }
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"success": False, "error": f"Booking not found: {booking_id}"}
        elif e.response.status_code == 400:
            try:
                error_detail = e.response.json().get("detail", "Cannot modify")
            except:
                error_detail = "Cannot modify this booking"
            return {"success": False, "error": error_detail}
        return {"success": False, "error": f"API error: {e.response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}