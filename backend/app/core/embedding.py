"""
ActionFlow - Embedding Service
OpenAI text-embedding-3-small ile metin vektörleştirme

Kullanım:
    from app.core.embedding import get_embedding, get_embeddings_batch
    
    # Tek metin
    vector = await get_embedding("Otel iptal politikası nedir?")
    
    # Toplu
    vectors = await get_embeddings_batch(["metin1", "metin2", "metin3"])
"""

import os
import logging
from typing import List, Optional
import openai
from openai import AsyncOpenAI

logger = logging.getLogger("ActionFlow-Embedding")

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small default

# OpenAI client (async)
_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """OpenAI client singleton"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


# ═══════════════════════════════════════════════════════════════════
# EMBEDDING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

async def get_embedding(text: str) -> List[float]:
    """
    Tek bir metin için embedding vektörü oluştur
    
    Args:
        text: Vektörleştirilecek metin
        
    Returns:
        1536 boyutlu float listesi
        
    Example:
        vector = await get_embedding("İptal politikası nedir?")
        # [0.123, -0.456, 0.789, ...]
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    # Metni temizle
    text = text.strip().replace("\n", " ")
    
    try:
        client = get_openai_client()
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        
        embedding = response.data[0].embedding
        logger.debug(f"Generated embedding for text: {text[:50]}...")
        
        return embedding
        
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise


async def get_embeddings_batch(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """
    Birden fazla metin için toplu embedding oluştur
    
    Args:
        texts: Vektörleştirilecek metin listesi
        batch_size: API çağrısı başına maksimum metin sayısı
        
    Returns:
        Her metin için embedding listesi
        
    Example:
        vectors = await get_embeddings_batch([
            "İptal politikası",
            "Bagaj kuralları",
            "İade süreci"
        ])
    """
    if not texts:
        return []
    
    # Metinleri temizle
    cleaned_texts = [t.strip().replace("\n", " ") for t in texts if t and t.strip()]
    
    if not cleaned_texts:
        raise ValueError("No valid texts provided")
    
    all_embeddings = []
    
    try:
        client = get_openai_client()
        
        # Batch'ler halinde işle
        for i in range(0, len(cleaned_texts), batch_size):
            batch = cleaned_texts[i:i + batch_size]
            
            response = await client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch
            )
            
            # Sıralı şekilde ekle
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
            
            logger.debug(f"Generated embeddings for batch {i//batch_size + 1}")
        
        logger.info(f"Generated {len(all_embeddings)} embeddings")
        return all_embeddings
        
    except openai.APIError as e:
        logger.error(f"OpenAI API error in batch: {e}")
        raise
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    İki vektör arasındaki kosinüs benzerliğini hesapla
    
    Args:
        vec1: İlk vektör
        vec2: İkinci vektör
        
    Returns:
        -1 ile 1 arasında benzerlik skoru (1 = en benzer)
    """
    import math
    
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have same length")
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def format_embedding_for_postgres(embedding: List[float]) -> str:
    """
    Embedding'i PostgreSQL pgvector formatına çevir
    
    Args:
        embedding: Float listesi
        
    Returns:
        PostgreSQL vector string: '[0.1,0.2,0.3,...]'
    """
    return "[" + ",".join(str(x) for x in embedding) + "]"


# ═══════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════

__all__ = [
    "get_embedding",
    "get_embeddings_batch",
    "cosine_similarity",
    "format_embedding_for_postgres",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSIONS"
]