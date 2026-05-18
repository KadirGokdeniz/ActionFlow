import json
import logging
import os
from typing import Optional
import redis.asyncio as redis

logger = logging.getLogger("ActionFlow-Redis")

# ═══════════════════════════════════════════════════════════════════
# REDIS CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Docker içerisinde servis adı 'redis' olduğu için varsayılan olarak onu kullanıyoruz
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Global Redis client (Singleton pattern)
_redis_client: Optional[redis.Redis] = None

async def get_redis() -> Optional[redis.Redis]:
    """
    Redis bağlantısını getirir veya oluşturur.
    Neden asenkron? Çünkü I/O işlemleri sırasında ana thread'i bloklamamalıyız.
    """
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                REDIS_URL, 
                encoding="utf-8", 
                decode_responses=True
            )
            # Bağlantıyı test et
            await _redis_client.ping()
            logger.info("⚡ Redis bağlantısı başarılı.")
        except Exception as e:
            logger.error(f"❌ Redis bağlantı hatası: {e}")
            return None
    return _redis_client

async def close_redis():
    """Uygulama kapanırken Redis bağlantısını güvenli bir şekilde sonlandırır."""
    global _redis_client
    if _redis_client:
        try:
            await _redis_client.aclose()
            logger.info("🛑 Redis bağlantısı kapatıldı.")
            _redis_client = None
        except Exception as e:
            logger.warning(f"⚠️ Redis kapatma hatası: {e}")

async def set_conversation_state(conversation_id: str, state: dict, ttl: int = 86400):
    """
    Konuşma durumunu Redis'e kaydeder.
    ttl (Time To Live): Varsayılan 24 saat (86400 sn).
    """
    client = await get_redis()
    if client:
        try:
            # Python dict objesini JSON string'e çeviriyoruz çünkü Redis string saklar
            await client.set(
                f"conv_state:{conversation_id}", 
                json.dumps(state), 
                ex=ttl
            )
        except Exception as e:
            logger.error(f"Redis set hatası: {e}")

async def get_conversation_state(conversation_id: str) -> Optional[dict]:
    """
    Konuşma durumunu Redis'ten getirir.
    Hız avantajı burada: PostgreSQL'e gitmeden RAM'den okuyoruz.
    """
    client = await get_redis()
    if client:
        try:
            data = await client.get(f"conv_state:{conversation_id}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Redis get hatası: {e}")
    return None

async def delete_conversation_state(conversation_id: str):
    """Konuşma sona erdiğinde veya silindiğinde cache'i temizler."""
    client = await get_redis()
    if client:
        try:
            await client.delete(f"conv_state:{conversation_id}")
        except Exception as e:
            logger.error(f"Redis delete hatası: {e}")
