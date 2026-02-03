"""
ActionFlow - Policy API Routes
Politika arama ve yönetim endpoint'leri

Endpoints:
    GET  /api/v1/policies/search?q=...     → Semantik arama
    GET  /api/v1/policies                   → Tüm politikaları listele
    GET  /api/v1/policies/{id}              → Politika detayı
    POST /api/v1/policies                   → Yeni politika ekle
    PUT  /api/v1/policies/{id}              → Politika güncelle
    DELETE /api/v1/policies/{id}            → Politika sil
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.policy_service import PolicyService

logger = logging.getLogger("ActionFlow-PolicyRoutes")

router = APIRouter(prefix="/api/v1/policies", tags=["Policies"])


# ═══════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════

class PolicySearchResult(BaseModel):
    """Arama sonucu"""
    id: str
    title: str
    content: str
    category: str
    provider: Optional[str]
    score: float
    effective_date: Optional[str]
    expiry_date: Optional[str]
    source_url: Optional[str]


class PolicySearchResponse(BaseModel):
    """Arama yanıtı"""
    success: bool
    query: str
    filters: dict
    count: int
    results: List[PolicySearchResult]


class PolicyCreateRequest(BaseModel):
    """Politika oluşturma isteği"""
    title: str = Field(..., min_length=5, max_length=255)
    content: str = Field(..., min_length=10)
    category: str = Field(..., pattern="^(cancellation|refund|baggage|check-in|general)$")
    provider: Optional[str] = Field(None, max_length=100)
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    source_url: Optional[str] = Field(None, max_length=500)


class PolicyUpdateRequest(BaseModel):
    """Politika güncelleme isteği"""
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    content: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = Field(None, pattern="^(cancellation|refund|baggage|check-in|general)$")
    provider: Optional[str] = Field(None, max_length=100)


class PolicyResponse(BaseModel):
    """Politika detay yanıtı"""
    id: str
    title: str
    content: str
    category: str
    provider: Optional[str]
    effective_date: Optional[str]
    expiry_date: Optional[str]
    source_url: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class PolicyListItem(BaseModel):
    """Liste item"""
    id: str
    title: str
    category: str
    provider: Optional[str]
    created_at: Optional[str]


# ═══════════════════════════════════════════════════════════════════
# SEARCH ENDPOINT
# ═══════════════════════════════════════════════════════════════════

@router.get("/search", response_model=PolicySearchResponse)
async def search_policies(
    q: str = Query(..., min_length=2, description="Arama sorgusu"),
    category: Optional[str] = Query(None, description="Kategori filtresi"),
    provider: Optional[str] = Query(None, description="Sağlayıcı filtresi"),
    limit: int = Query(5, ge=1, le=20, description="Maksimum sonuç sayısı"),
    min_score: float = Query(0.5, ge=0, le=1, description="Minimum benzerlik skoru"),
    db: AsyncSession = Depends(get_db)
):
    """
    Semantik politika araması
    
    Doğal dil sorgusu ile ilgili politikaları bulur.
    pgvector cosine similarity kullanır.
    
    Örnek sorgular:
    - "otel iptal politikası nedir?"
    - "bagaj hakkım ne kadar?"
    - "THY bilet iadesi nasıl yapılır?"
    """
    logger.info(f"Policy search: q='{q}', category={category}, provider={provider}")
    
    try:
        service = PolicyService(db)
        results = await service.search(
            query=q,
            category=category,
            provider=provider,
            limit=limit,
            min_score=min_score
        )
        
        return PolicySearchResponse(
            success=True,
            query=q,
            filters={"category": category, "provider": provider},
            count=len(results),
            results=[PolicySearchResult(**r.to_dict()) for r in results]
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Alternatif endpoint (path parameter ile)
@router.get("/search/{query}", response_model=PolicySearchResponse)
async def search_policies_path(
    query: str,
    category: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """Alternatif arama endpoint'i (path parameter)"""
    return await search_policies(
        q=query,
        category=category,
        provider=provider,
        limit=limit,
        db=db
    )


# ═══════════════════════════════════════════════════════════════════
# CRUD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@router.get("", response_model=List[PolicyListItem])
async def list_policies(
    category: Optional[str] = Query(None, description="Kategori filtresi"),
    provider: Optional[str] = Query(None, description="Sağlayıcı filtresi"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Tüm politikaları listele"""
    service = PolicyService(db)
    policies = await service.get_all(
        category=category,
        provider=provider,
        limit=limit
    )
    return [PolicyListItem(**p) for p in policies]


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Politika detayı"""
    service = PolicyService(db)
    policy = await service.get_by_id(policy_id)
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return PolicyResponse(**policy)


@router.post("", response_model=dict)
async def create_policy(
    request: PolicyCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Yeni politika ekle
    
    Embedding otomatik oluşturulur.
    """
    logger.info(f"Creating policy: {request.title}")
    
    try:
        from datetime import datetime
        
        service = PolicyService(db)
        
        # Tarihleri parse et
        effective_date = None
        expiry_date = None
        
        if request.effective_date:
            effective_date = datetime.fromisoformat(request.effective_date)
        if request.expiry_date:
            expiry_date = datetime.fromisoformat(request.expiry_date)
        
        policy_id = await service.create(
            title=request.title,
            content=request.content,
            category=request.category,
            provider=request.provider,
            effective_date=effective_date,
            expiry_date=expiry_date,
            source_url=request.source_url
        )
        
        return {"success": True, "id": policy_id, "message": "Policy created"}
        
    except Exception as e:
        logger.error(f"Create failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{policy_id}", response_model=dict)
async def update_policy(
    policy_id: str,
    request: PolicyUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Politika güncelle
    
    İçerik değişirse embedding yeniden oluşturulur.
    """
    logger.info(f"Updating policy: {policy_id}")
    
    try:
        service = PolicyService(db)
        updated = await service.update(
            policy_id=policy_id,
            title=request.title,
            content=request.content,
            category=request.category,
            provider=request.provider
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        return {"success": True, "id": policy_id, "message": "Policy updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{policy_id}", response_model=dict)
async def delete_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Politika sil"""
    logger.info(f"Deleting policy: {policy_id}")
    
    try:
        service = PolicyService(db)
        deleted = await service.delete(policy_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Policy not found")
        
        return {"success": True, "id": policy_id, "message": "Policy deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@router.get("/categories/list", response_model=dict)
async def list_categories():
    """Mevcut kategorileri listele"""
    return {
        "categories": [
            {"id": "cancellation", "name": "İptal Politikaları", "name_en": "Cancellation Policies"},
            {"id": "refund", "name": "İade Politikaları", "name_en": "Refund Policies"},
            {"id": "baggage", "name": "Bagaj Kuralları", "name_en": "Baggage Rules"},
            {"id": "check-in", "name": "Check-in Prosedürleri", "name_en": "Check-in Procedures"},
            {"id": "general", "name": "Genel Kurallar", "name_en": "General Rules"}
        ]
    }


@router.post("/rebuild-embeddings", response_model=dict)
async def rebuild_embeddings(
    db: AsyncSession = Depends(get_db)
):
    """
    Tüm politikaların embedding'lerini yeniden oluştur
    
    DİKKAT: Bu işlem uzun sürebilir ve API maliyeti oluşturur.
    Sadece model değişikliği sonrası kullanın.
    """
    logger.warning("Rebuilding all policy embeddings...")
    
    try:
        service = PolicyService(db)
        count = await service.rebuild_embeddings()
        
        return {
            "success": True,
            "message": f"Rebuilt embeddings for {count} policies"
        }
        
    except Exception as e:
        logger.error(f"Rebuild failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))