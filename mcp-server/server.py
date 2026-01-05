"""
ActionFlow MCP Server - SSE (Server-Sent Events) Tabanlı
HTTP üzerinden erişilebilir, production-ready MCP Server

Bu server, LLM'lerin (Claude, GPT, vb.) ActionFlow backend'indeki
işlevleri tool olarak kullanmasını sağlar.
"""

import os
import json
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Any
import uuid

load_dotenv()

# Backend URL (Docker network içinde)
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

# HTTP client
http_client = None


# ═══════════════════════════════════════════════════════════════════
# TOOL TANIMLARI
# ═══════════════════════════════════════════════════════════════════

TOOLS = [
    {
        "name": "search_hotels",
        "description": "Belirtilen şehirde otel arar. Şehir kodu IATA formatında olmalı (PAR=Paris, IST=İstanbul, AMS=Amsterdam, LON=Londra gibi).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "city_code": {
                    "type": "string",
                    "description": "IATA şehir kodu (örn: PAR, IST, LON, AMS)"
                },
                "radius": {
                    "type": "integer",
                    "description": "Arama yarıçapı km cinsinden (varsayılan: 5)",
                    "default": 5
                }
            },
            "required": ["city_code"]
        }
    },
    {
        "name": "get_hotel_offers",
        "description": "Belirli oteller için fiyat ve müsaitlik bilgisi alır. Tarihler YYYY-MM-DD formatında olmalı.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hotel_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Otel ID listesi (en fazla 20)"
                },
                "check_in": {
                    "type": "string",
                    "description": "Giriş tarihi (YYYY-MM-DD)"
                },
                "check_out": {
                    "type": "string",
                    "description": "Çıkış tarihi (YYYY-MM-DD)"
                },
                "adults": {
                    "type": "integer",
                    "description": "Yetişkin sayısı (varsayılan: 1)",
                    "default": 1
                }
            },
            "required": ["hotel_ids", "check_in", "check_out"]
        }
    },
    {
        "name": "search_flights",
        "description": "İki şehir arasında uçuş arar. Şehir kodları IATA formatında olmalı.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Kalkış şehri IATA kodu (örn: IST)"
                },
                "destination": {
                    "type": "string",
                    "description": "Varış şehri IATA kodu (örn: PAR)"
                },
                "date": {
                    "type": "string",
                    "description": "Uçuş tarihi (YYYY-MM-DD)"
                },
                "adults": {
                    "type": "integer",
                    "description": "Yolcu sayısı (varsayılan: 1)",
                    "default": 1
                },
                "return_date": {
                    "type": "string",
                    "description": "Dönüş tarihi (opsiyonel, YYYY-MM-DD)"
                }
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "get_user_bookings",
        "description": "Kullanıcının mevcut rezervasyonlarını listeler.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Kullanıcı ID"
                }
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "cancel_booking",
        "description": "Bir rezervasyonu iptal eder. DİKKAT: Bu işlem geri alınamaz!",
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
    },
    {
        "name": "search_policies",
        "description": "İptal, iade, bagaj gibi politikaları arar.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Arama sorgusu (örn: 'iptal politikası', 'bagaj hakkı')"
                },
                "category": {
                    "type": "string",
                    "description": "Kategori filtresi (opsiyonel: cancellation, refund, baggage, check-in)"
                }
            },
            "required": ["query"]
        }
    }
]


# ═══════════════════════════════════════════════════════════════════
# TOOL UYGULAMALARI
# ═══════════════════════════════════════════════════════════════════

async def search_hotels(city_code: str, radius: int = 5) -> dict:
    """Şehirde otel ara"""
    try:
        response = await http_client.get(
            f"/hotels/search/city/{city_code.upper()}",
            params={"radius": radius}
        )
        response.raise_for_status()
        data = response.json()
        
        hotels = data.get("hotels", [])[:10]
        return {
            "success": True,
            "city": city_code.upper(),
            "count": data.get("count", 0),
            "hotels": [
                {
                    "id": h.get("hotelId"),
                    "name": h.get("name"),
                    "distance": h.get("distance", {}).get("value"),
                }
                for h in hotels
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_hotel_offers(hotel_ids: list, check_in: str, check_out: str, adults: int = 1) -> dict:
    """Otel fiyatlarını al"""
    try:
        response = await http_client.post(
            "/hotels/offers",
            json={
                "hotel_ids": hotel_ids[:20],
                "check_in": check_in,
                "check_out": check_out,
                "adults": adults,
                "rooms": 1,
                "currency": "EUR"
            }
        )
        response.raise_for_status()
        data = response.json()
        
        offers = data.get("offers", [])
        return {
            "success": True,
            "check_in": check_in,
            "check_out": check_out,
            "count": len(offers),
            "offers": [
                {
                    "hotel_id": o.get("hotel", {}).get("hotelId"),
                    "hotel_name": o.get("hotel", {}).get("name"),
                    "price": o.get("offers", [{}])[0].get("price", {}).get("total") if o.get("offers") else None,
                    "currency": o.get("offers", [{}])[0].get("price", {}).get("currency") if o.get("offers") else None,
                }
                for o in offers
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def search_flights(origin: str, destination: str, date: str, adults: int = 1, return_date: str = None) -> dict:
    """Uçuş ara"""
    try:
        params = {
            "origin": origin.upper(),
            "destination": destination.upper(),
            "date": date,
            "adults": adults,
            "max_results": 5
        }
        if return_date:
            params["return_date"] = return_date
            
        response = await http_client.get("/flights/search", params=params)
        response.raise_for_status()
        data = response.json()
        
        flights = data.get("flights", [])
        return {
            "success": True,
            "route": f"{origin.upper()} → {destination.upper()}",
            "date": date,
            "count": data.get("count", 0),
            "cheapest": data.get("cheapest"),
            "flights": [
                {
                    "price": f.get("price", {}).get("total"),
                    "currency": f.get("price", {}).get("currency"),
                    "duration": f.get("itineraries", [{}])[0].get("duration") if f.get("itineraries") else None,
                    "stops": len(f.get("itineraries", [{}])[0].get("segments", [])) - 1 if f.get("itineraries") else 0
                }
                for f in flights[:5]
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_user_bookings(user_id: str) -> dict:
    """Kullanıcının rezervasyonlarını al"""
    try:
        response = await http_client.get(f"/users/{user_id}/bookings")
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "user_id": user_id,
            "count": data.get("count", 0),
            "bookings": data.get("bookings", [])
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def cancel_booking(booking_id: str, reason: str = None) -> dict:
    """Rezervasyon iptal et"""
    try:
        response = await http_client.delete(f"/flights/orders/{booking_id}")
        response.raise_for_status()
        
        return {
            "success": True,
            "booking_id": booking_id,
            "status": "cancelled",
            "reason": reason,
            "message": "Rezervasyon başarıyla iptal edildi."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def search_policies(query: str, category: str = None) -> dict:
    """Politika ara"""
    try:
        url = f"/policies/search/{query}"
        params = {}
        if category:
            params["category"] = category
            
        response = await http_client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        return {
            "success": True,
            "query": query,
            "count": data.get("count", 0),
            "results": data.get("results", [])
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Tool fonksiyonlarını eşle
TOOL_FUNCTIONS = {
    "search_hotels": search_hotels,
    "get_hotel_offers": get_hotel_offers,
    "search_flights": search_flights,
    "get_user_bookings": get_user_bookings,
    "cancel_booking": cancel_booking,
    "search_policies": search_policies,
}


# ═══════════════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup ve shutdown işlemleri"""
    global http_client
    http_client = httpx.AsyncClient(base_url=BACKEND_URL, timeout=30.0)
    print(f"MCP Server başlatıldı. Backend: {BACKEND_URL}")
    yield
    await http_client.aclose()
    print("MCP Server kapatıldı.")


app = FastAPI(
    title="ActionFlow MCP Server",
    description="Travel AI Tool Server - SSE tabanlı MCP protokolü",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════
# MCP PROTOCOL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Server bilgisi"""
    return {
        "name": "ActionFlow MCP Server",
        "version": "1.0.0",
        "protocol": "MCP over SSE",
        "tools_count": len(TOOLS),
        "backend": BACKEND_URL
    }


@app.get("/health")
async def health():
    """Health check"""
    try:
        response = await http_client.get("/health")
        backend_status = "connected" if response.status_code == 200 else "error"
    except:
        backend_status = "disconnected"
    
    return {
        "status": "healthy",
        "backend": backend_status
    }


@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint - MCP Inspector bu endpoint'e bağlanır"""
    
    async def event_generator():
        # İlk bağlantıda server info gönder
        yield f"data: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"
        
        # Bağlantıyı açık tut
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'type': 'ping'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/message")
@app.post("/mcp/message")
async def handle_message(request: Request):
    """MCP mesajlarını işle"""
    try:
        body = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    
    method = body.get("method", "")
    params = body.get("params", {})
    msg_id = body.get("id", str(uuid.uuid4()))
    
    # Initialize
    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "ActionFlow MCP Server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {"listChanged": True}
                }
            }
        })
    
    # List tools
    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": TOOLS
            }
        })
    
    # Call tool
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in TOOL_FUNCTIONS:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                }
            })
        
        try:
            result = await TOOL_FUNCTIONS[tool_name](**arguments)
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            })
        except Exception as e:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            })
    
    # Notifications
    elif method == "notifications/initialized":
        return JSONResponse({"jsonrpc": "2.0", "id": msg_id, "result": {}})
    
    # Unknown method
    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        })


# ═══════════════════════════════════════════════════════════════════
# DOĞRUDAN TEST ENDPOINT'LERİ
# ═══════════════════════════════════════════════════════════════════

@app.get("/tools")
async def list_tools():
    """Tool listesini döndür (test için)"""
    return {"tools": TOOLS}


@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: Request):
    """Tool'u çağır (test için)"""
    if tool_name not in TOOL_FUNCTIONS:
        return JSONResponse({"error": f"Tool not found: {tool_name}"}, status_code=404)
    
    try:
        body = await request.json()
    except:
        body = {}
    
    try:
        result = await TOOL_FUNCTIONS[tool_name](**body)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
