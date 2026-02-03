"""
ActionFlow - Policy Service
Politika CRUD işlemleri ve pgvector ile semantik arama

Kullanım:
    from app.services.policy_service import PolicyService
    
    service = PolicyService(db_session)
    
    # Arama
    results = await service.search("iptal politikası", limit=5)
    
    # Ekleme
    policy = await service.create(title="...", content="...", category="cancellation")
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embedding import get_embedding, format_embedding_for_postgres

logger = logging.getLogger("ActionFlow-PolicyService")


# ═══════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════

class PolicyResult:
    """Arama sonucu modeli"""
    def __init__(
        self,
        id: str,
        title: str,
        content: str,
        category: str,
        provider: Optional[str],
        score: float,
        effective_date: Optional[datetime] = None,
        expiry_date: Optional[datetime] = None,
        source_url: Optional[str] = None
    ):
        self.id = id
        self.title = title
        self.content = content
        self.category = category
        self.provider = provider
        self.score = score
        self.effective_date = effective_date
        self.expiry_date = expiry_date
        self.source_url = source_url
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "provider": self.provider,
            "score": round(self.score, 4),
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "source_url": self.source_url
        }


# ═══════════════════════════════════════════════════════════════════
# POLICY SERVICE
# ═══════════════════════════════════════════════════════════════════

class PolicyService:
    """
    Politika yönetimi ve semantik arama servisi
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ─────────────────────────────────────────────────────────────
    # SEARCH (Semantic)
    # ─────────────────────────────────────────────────────────────
    
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        provider: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.5
    ) -> List[PolicyResult]:
        """
        Semantik politika araması
        
        Args:
            query: Arama sorgusu (doğal dil)
            category: Kategori filtresi (cancellation, refund, baggage, check-in, general)
            provider: Sağlayıcı filtresi (Turkish Airlines, Pegasus, vb.)
            limit: Maksimum sonuç sayısı
            min_score: Minimum benzerlik skoru (0-1)
            
        Returns:
            Benzerlik skoruna göre sıralı PolicyResult listesi
        """
        logger.info(f"Searching policies: query='{query}', category={category}, provider={provider}")
        
        try:
            # Sorgu için embedding oluştur
            query_embedding = await get_embedding(query)
            embedding_str = format_embedding_for_postgres(query_embedding)
            
            # SQL sorgusu oluştur (pgvector cosine similarity)
            # 1 - distance = similarity (cosine distance → similarity)
            sql = """
                SELECT 
                    id,
                    title,
                    content,
                    category,
                    provider,
                    effective_date,
                    expiry_date,
                    source_url,
                    1 - (content_embedding <=> cast(:embedding as vector)) as similarity
                FROM policies
                WHERE content_embedding IS NOT NULL
            """
            
            params = {"embedding": embedding_str}
            
            # Filtreler
            if category:
                sql += " AND category = :category"
                params["category"] = category
            
            if provider:
                sql += " AND (provider = :provider OR provider IS NULL OR provider = 'general')"
                params["provider"] = provider
            
            # Minimum skor filtresi
            sql += " AND 1 - (content_embedding <=> cast(:embedding as vector)) >= :min_score"
            params["min_score"] = min_score
            
            # Sıralama ve limit
            sql += " ORDER BY similarity DESC LIMIT :limit"
            params["limit"] = limit
            
            # Sorguyu çalıştır
            result = await self.db.execute(text(sql), params)
            rows = result.fetchall()
            
            # Sonuçları dönüştür
            results = []
            for row in rows:
                results.append(PolicyResult(
                    id=row.id,
                    title=row.title,
                    content=row.content,
                    category=row.category,
                    provider=row.provider,
                    score=float(row.similarity),
                    effective_date=row.effective_date,
                    expiry_date=row.expiry_date,
                    source_url=row.source_url
                ))
            
            logger.info(f"Found {len(results)} policies for query: {query[:30]}...")
            return results
            
        except Exception as e:
            logger.error(f"Policy search failed: {e}")
            raise
    
    # ─────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────
    
    async def create(
        self,
        title: str,
        content: str,
        category: str,
        provider: Optional[str] = None,
        effective_date: Optional[datetime] = None,
        expiry_date: Optional[datetime] = None,
        source_url: Optional[str] = None
    ) -> str:
        """
        Yeni politika ekle (embedding otomatik oluşturulur)
        
        Args:
            title: Politika başlığı
            content: Politika içeriği
            category: Kategori (cancellation, refund, baggage, check-in, general)
            provider: Sağlayıcı (Turkish Airlines, Pegasus, vb.)
            effective_date: Geçerlilik başlangıç tarihi
            expiry_date: Geçerlilik bitiş tarihi
            source_url: Kaynak URL
            
        Returns:
            Oluşturulan politika ID'si
        """
        logger.info(f"Creating policy: {title}")
        
        try:
            # ID oluştur
            policy_id = f"policy-{uuid.uuid4().hex[:8]}"
            
            # Embedding oluştur (title + content birlikte)
            embedding_text = f"{title}. {content}"
            embedding = await get_embedding(embedding_text)
            embedding_str = format_embedding_for_postgres(embedding)
            
            # SQL insert
            sql = """
                INSERT INTO policies (
                    id, title, content, category, provider,
                    effective_date, expiry_date, source_url,
                    content_embedding, created_at, updated_at
                ) VALUES (
                    :id, :title, :content, :category, :provider,
                    :effective_date, :expiry_date, :source_url,
                    cast(:embedding as vector), NOW(), NOW()
                )
            """
            
            await self.db.execute(text(sql), {
                "id": policy_id,
                "title": title,
                "content": content,
                "category": category,
                "provider": provider,
                "effective_date": effective_date,
                "expiry_date": expiry_date,
                "source_url": source_url,
                "embedding": embedding_str
            })
            
            await self.db.commit()
            
            logger.info(f"Created policy: {policy_id}")
            return policy_id
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Policy creation failed: {e}")
            raise
    
    # ─────────────────────────────────────────────────────────────
    # READ
    # ─────────────────────────────────────────────────────────────
    
    async def get_by_id(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """ID'ye göre politika getir"""
        sql = """
            SELECT id, title, content, category, provider,
                   effective_date, expiry_date, source_url,
                   created_at, updated_at
            FROM policies
            WHERE id = :id
        """
        
        result = await self.db.execute(text(sql), {"id": policy_id})
        row = result.fetchone()
        
        if not row:
            return None
        
        return {
            "id": row.id,
            "title": row.title,
            "content": row.content,
            "category": row.category,
            "provider": row.provider,
            "effective_date": row.effective_date.isoformat() if row.effective_date else None,
            "expiry_date": row.expiry_date.isoformat() if row.expiry_date else None,
            "source_url": row.source_url,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None
        }
    
    async def get_all(
        self,
        category: Optional[str] = None,
        provider: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Tüm politikaları listele"""
        sql = """
            SELECT id, title, category, provider, created_at
            FROM policies
            WHERE 1=1
        """
        params = {}
        
        if category:
            sql += " AND category = :category"
            params["category"] = category
        
        if provider:
            sql += " AND provider = :provider"
            params["provider"] = provider
        
        sql += " ORDER BY created_at DESC LIMIT :limit"
        params["limit"] = limit
        
        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()
        
        return [
            {
                "id": row.id,
                "title": row.title,
                "category": row.category,
                "provider": row.provider,
                "created_at": row.created_at.isoformat() if row.created_at else None
            }
            for row in rows
        ]
    
    # ─────────────────────────────────────────────────────────────
    # UPDATE
    # ─────────────────────────────────────────────────────────────
    
    async def update(
        self,
        policy_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        provider: Optional[str] = None
    ) -> bool:
        """
        Politika güncelle (içerik değişirse embedding yeniden oluşturulur)
        """
        logger.info(f"Updating policy: {policy_id}")
        
        try:
            # Mevcut politikayı al
            existing = await self.get_by_id(policy_id)
            if not existing:
                return False
            
            # Güncellenecek alanları belirle
            updates = []
            params = {"id": policy_id}
            
            new_title = title or existing["title"]
            new_content = content or existing["content"]
            
            if title:
                updates.append("title = :title")
                params["title"] = title
            
            if content:
                updates.append("content = :content")
                params["content"] = content
            
            if category:
                updates.append("category = :category")
                params["category"] = category
            
            if provider:
                updates.append("provider = :provider")
                params["provider"] = provider
            
            # İçerik değiştiyse embedding'i güncelle
            if title or content:
                embedding_text = f"{new_title}. {new_content}"
                embedding = await get_embedding(embedding_text)
                embedding_str = format_embedding_for_postgres(embedding)
                updates.append("content_embedding = cast(:embedding as vector)")
                params["embedding"] = embedding_str
            
            updates.append("updated_at = NOW()")
            
            sql = f"UPDATE policies SET {', '.join(updates)} WHERE id = :id"
            
            await self.db.execute(text(sql), params)
            await self.db.commit()
            
            logger.info(f"Updated policy: {policy_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Policy update failed: {e}")
            raise
    
    # ─────────────────────────────────────────────────────────────
    # DELETE
    # ─────────────────────────────────────────────────────────────
    
    async def delete(self, policy_id: str) -> bool:
        """Politika sil"""
        logger.info(f"Deleting policy: {policy_id}")
        
        try:
            sql = "DELETE FROM policies WHERE id = :id"
            result = await self.db.execute(text(sql), {"id": policy_id})
            await self.db.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted policy: {policy_id}")
            else:
                logger.warning(f"Policy not found: {policy_id}")
            
            return deleted
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Policy deletion failed: {e}")
            raise
    
    # ─────────────────────────────────────────────────────────────
    # BULK OPERATIONS
    # ─────────────────────────────────────────────────────────────
    
    async def bulk_create(self, policies: List[Dict[str, Any]]) -> List[str]:
        """
        Toplu politika ekleme
        
        Args:
            policies: Politika listesi [{"title": ..., "content": ..., "category": ...}, ...]
            
        Returns:
            Oluşturulan policy ID'leri
        """
        logger.info(f"Bulk creating {len(policies)} policies")
        
        created_ids = []
        
        for policy in policies:
            policy_id = await self.create(
                title=policy["title"],
                content=policy["content"],
                category=policy["category"],
                provider=policy.get("provider"),
                effective_date=policy.get("effective_date"),
                expiry_date=policy.get("expiry_date"),
                source_url=policy.get("source_url")
            )
            created_ids.append(policy_id)
        
        logger.info(f"Bulk created {len(created_ids)} policies")
        return created_ids
    
    async def rebuild_embeddings(self) -> int:
        """
        Tüm politikaların embedding'lerini yeniden oluştur
        (Model değişikliği sonrası kullanılır)
        """
        logger.info("Rebuilding all policy embeddings...")
        
        # Tüm politikaları al
        sql = "SELECT id, title, content FROM policies"
        result = await self.db.execute(text(sql))
        rows = result.fetchall()
        
        count = 0
        for row in rows:
            embedding_text = f"{row.title}. {row.content}"
            embedding = await get_embedding(embedding_text)
            embedding_str = format_embedding_for_postgres(embedding)
            
            update_sql = """
                UPDATE policies 
                SET content_embedding = cast(:embedding as vector), updated_at = NOW()
                WHERE id = :id
            """
            await self.db.execute(text(update_sql), {
                "id": row.id,
                "embedding": embedding_str
            })
            count += 1
        
        await self.db.commit()
        logger.info(f"Rebuilt embeddings for {count} policies")
        return count


# ═══════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════

__all__ = ["PolicyService", "PolicyResult"]