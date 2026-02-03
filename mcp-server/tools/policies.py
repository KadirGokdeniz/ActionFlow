"""
ActionFlow MCP Tools - Policy Search (RAG)
İptal, iade, bagaj politikaları için semantic search
"""

from typing import Optional
import httpx


# ═══════════════════════════════════════════════════════════════════
# TOOL DEFINITION (MCP Schema)
# ═══════════════════════════════════════════════════════════════════

TOOL_DEFINITION = {
    "name": "search_policies",
    "description": "Seyahat politikalarını arar: iptal kuralları, iade koşulları, bagaj hakları, check-in prosedürleri vb. Sorgunuzu doğal dilde yazabilirsiniz.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Arama sorgusu (örn: 'iptal politikası', 'bagaj hakkım ne kadar', 'iade ne zaman yatar')"
            },
            "category": {
                "type": "string",
                "description": "Kategori filtresi (opsiyonel)",
                "enum": ["cancellation", "refund", "baggage", "check-in", "general"],
            },
            "provider": {
                "type": "string",
                "description": "Havayolu veya otel adı filtresi (opsiyonel, örn: 'Turkish Airlines', 'Hilton')"
            }
        },
        "required": ["query"]
    }
}


# ═══════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════

async def search_policies(
    query: str,
    category: Optional[str] = None,
    provider: Optional[str] = None,
    http_client: httpx.AsyncClient = None
) -> dict:
    """
    Politika arar (semantic search)
    
    Args:
        query: Arama sorgusu
        category: Kategori filtresi
        provider: Sağlayıcı filtresi
        http_client: HTTP client
    
    Returns:
        İlgili politikalar veya hata
    """
    if http_client is None:
        return {"success": False, "error": "HTTP client not provided"}
    
    try:
        # Query parameters
        params = {}
        if category:
            params["category"] = category
        if provider:
            params["provider"] = provider
        
        # Backend'e RAG sorgusu gönder
        response = await http_client.get(
            f"/api/v1/policies/search/{query}",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        
        if not results:
            return {
                "success": True,
                "query": query,
                "count": 0,
                "message": f"'{query}' ile ilgili politika bulunamadı.",
                "suggestions": [
                    "Farklı anahtar kelimeler deneyin",
                    "Kategori filtresi ekleyin (cancellation, refund, baggage, check-in)",
                    "Daha genel bir sorgu yapın"
                ]
            }
        
        # Sonuçları formatla
        formatted_results = []
        for r in results:
            policy_info = {
                "title": r.get("title"),
                "category": r.get("category"),
                "provider": r.get("provider", "Genel"),
                "content": r.get("content"),
                "relevance_score": r.get("score"),
            }
            
            # Geçerlilik tarihleri
            if r.get("effective_date"):
                policy_info["effective_date"] = r.get("effective_date")
            if r.get("expiry_date"):
                policy_info["expiry_date"] = r.get("expiry_date")
            
            # Kaynak
            if r.get("source_url"):
                policy_info["source"] = r.get("source_url")
            
            formatted_results.append(policy_info)
        
        return {
            "success": True,
            "query": query,
            "filters": {
                "category": category,
                "provider": provider
            },
            "count": len(formatted_results),
            "results": formatted_results
        }
        
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"API error: {e.response.status_code}",
            "detail": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ═══════════════════════════════════════════════════════════════════
# HELPER: Kategori Açıklamaları
# ═══════════════════════════════════════════════════════════════════

CATEGORY_DESCRIPTIONS = {
    "cancellation": "İptal koşulları, ücretsiz iptal süreleri, iptal ücretleri",
    "refund": "İade süreçleri, iade süreleri, kısmi iade koşulları",
    "baggage": "Bagaj hakları, el bagajı kuralları, fazla bagaj ücretleri",
    "check-in": "Online check-in, havalimanı check-in, check-in saatleri",
    "general": "Genel seyahat kuralları, değişiklik politikaları"
}


def get_category_help() -> dict:
    """Kategori yardım bilgisi döndürür"""
    return {
        "available_categories": list(CATEGORY_DESCRIPTIONS.keys()),
        "descriptions": CATEGORY_DESCRIPTIONS
    }