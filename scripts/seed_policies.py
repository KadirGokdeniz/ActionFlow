"""
ActionFlow - Database Seed Script
Örnek policy verileri ekler (RAG için)

Kullanım:
    python -m scripts.seed_policies
    
    veya Docker içinde:
    docker exec actionflow-backend python -m scripts.seed_policies
"""

import asyncio
import uuid
from datetime import datetime

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import (
    get_async_session_maker,
    init_db,
    Policy,
    get_embedding,
    PGVECTOR_AVAILABLE
)


# ═══════════════════════════════════════════════════════════════════
# SAMPLE POLICIES DATA
# ═══════════════════════════════════════════════════════════════════

SAMPLE_POLICIES = [
    # ─────────────── CANCELLATION ───────────────
    {
        "category": "cancellation",
        "provider": "general",
        "title": "Genel Uçuş İptal Politikası",
        "content": """Uçuş iptali için genel kurallar:
        
1. Kalkıştan 24 saat öncesine kadar ücretsiz iptal yapılabilir (bilet alımından sonraki 24 saat içinde).
2. 7 gün veya daha önce iptal: Tam iade
3. 3-7 gün arası iptal: %50 iade
4. 3 günden az: İade yapılmaz

Esnek biletlerde (Flex fare) farklı kurallar geçerli olabilir. Bilet detaylarınızı kontrol edin."""
    },
    {
        "category": "cancellation",
        "provider": "Turkish Airlines",
        "title": "Turkish Airlines İptal Politikası",
        "content": """Turkish Airlines uçuş iptali:

- EcoFly: İptal ücreti uygulanır, iade bilet türüne göre değişir
- ExtraFly: Kalkıştan 3 saat öncesine kadar ücretsiz değişiklik
- PrimeFly: Tam esneklik, ücretsiz iptal ve değişiklik

Miles&Smiles üyeleri için ek avantajlar mevcuttur. İptal işlemi thy.com üzerinden veya çağrı merkezi aracılığıyla yapılabilir."""
    },
    {
        "category": "cancellation",
        "provider": "general",
        "title": "Otel Rezervasyon İptal Politikası",
        "content": """Otel iptal kuralları:

- Ücretsiz iptal: Check-in tarihinden 24-48 saat öncesine kadar (otele göre değişir)
- Geç iptal: Genellikle 1 gecelik konaklama ücreti kesilir
- No-show (gelmeme): Tam ücret tahsil edilir

Özel dönemlerde (bayram, yılbaşı) daha katı kurallar uygulanabilir. Rezervasyon onay e-postanızdaki iptal koşullarını kontrol edin."""
    },
    
    # ─────────────── REFUND ───────────────
    {
        "category": "refund",
        "provider": "general",
        "title": "İade Süreci ve Süreleri",
        "content": """İade işlemi süreci:

1. İptal onaylandıktan sonra iade işlemi başlatılır
2. Kredi kartı iadeleri: 5-10 iş günü
3. Banka havalesi iadeleri: 3-5 iş günü
4. Miles iadesi: Anında hesaba yansır

İade tutarı, iptal zamanına ve bilet türüne göre hesaplanır. Vergiler ve harçlar genellikle tam iade edilir."""
    },
    {
        "category": "refund",
        "provider": "general",
        "title": "Kısmi İade Koşulları",
        "content": """Kısmi iade yapılan durumlar:

- Geç iptal (3-7 gün öncesi): %50 iade
- Bilet türü değişikliği: Fark iade edilir veya tahsil edilir
- Downgrade (düşük sınıfa geçiş): Fark iade edilir

İptal ücretleri düşüldükten sonra kalan tutar iade edilir. İade detayları için rezervasyon onay e-postanızı kontrol edin."""
    },
    
    # ─────────────── BAGGAGE ───────────────
    {
        "category": "baggage",
        "provider": "general",
        "title": "Genel Bagaj Kuralları",
        "content": """Bagaj hakları (ekonomi sınıfı):

El Bagajı:
- Boyut: 55x40x23 cm
- Ağırlık: 8 kg (havayoluna göre değişir)
- Adet: 1 parça + kişisel eşya

Kayıtlı Bagaj:
- Standart: 23 kg
- Business: 32 kg
- Fazla bagaj ücreti: kg başına 5-15 EUR

Özel eşyalar (spor malzemesi, müzik aleti) için önceden bildirim gerekebilir."""
    },
    {
        "category": "baggage",
        "provider": "Turkish Airlines",
        "title": "Turkish Airlines Bagaj Hakkı",
        "content": """Turkish Airlines bagaj kuralları:

EcoFly:
- El bagajı: 8 kg
- Kayıtlı bagaj: 15-25 kg (rotaya göre)

ExtraFly:
- El bagajı: 8 kg
- Kayıtlı bagaj: 25-30 kg

PrimeFly / Business:
- El bagajı: 8 kg
- Kayıtlı bagaj: 2x32 kg

Miles&Smiles Elite/Elite Plus üyelerine ek bagaj hakkı tanınır."""
    },
    
    # ─────────────── CHECK-IN ───────────────
    {
        "category": "check-in",
        "provider": "general",
        "title": "Online Check-in Bilgileri",
        "content": """Online check-in:

- Açılış: Kalkıştan 24-48 saat önce (havayoluna göre)
- Kapanış: Kalkıştan 1-3 saat önce
- Mobil biniş kartı: QR kod olarak telefona kaydedilebilir

Online check-in avantajları:
- Koltuk seçimi
- Havalimanında zaman tasarrufu
- Erken biniş imkanı (bazı havayollarında)"""
    },
    {
        "category": "check-in",
        "provider": "general",
        "title": "Havalimanı Check-in Süreleri",
        "content": """Havalimanında check-in kapanış süreleri:

Yurtiçi uçuşlar:
- Check-in kapanış: 45 dakika önce
- Biniş kapısı kapanış: 20 dakika önce

Yurtdışı uçuşlar:
- Check-in kapanış: 60-90 dakika önce
- Biniş kapısı kapanış: 30 dakika önce

Erken gelin! Güvenlik ve pasaport kontrolü zaman alabilir."""
    },
    
    # ─────────────── GENERAL ───────────────
    {
        "category": "general",
        "provider": "general",
        "title": "Uçuş Değişikliği Kuralları",
        "content": """Uçuş değişikliği:

- Tarih değişikliği: Bilet türüne göre ücretsiz veya ücretli
- Rota değişikliği: Genellikle fark ücreti uygulanır
- İsim değişikliği: Çoğu havayolunda yapılamaz

Değişiklik yapmak için:
1. Havayolu web sitesi veya uygulaması
2. Çağrı merkezi
3. Seyahat acentası (aracılık ücreti olabilir)"""
    },
    {
        "category": "general",
        "provider": "general",
        "title": "Özel Yardım Hizmetleri",
        "content": """Özel yardım gerektiren yolcular:

- Tekerlekli sandalye: Uçuştan 48 saat önce talep edin
- Refakatsiz çocuk: Havayolu kurallarına göre 5-12 yaş arası
- Tıbbi cihaz: Önceden onay gerekebilir
- Evcil hayvan: Kabin veya kargo (önceden rezervasyon şart)

Özel yardım talepleri için havayolu müşteri hizmetleri ile iletişime geçin."""
    },
]


# ═══════════════════════════════════════════════════════════════════
# SEED FUNCTION
# ═══════════════════════════════════════════════════════════════════

async def seed_policies():
    """Policy tablosuna örnek veriler ekler"""
    
    print("🌱 Starting policy seed...")
    
    # Initialize database
    await init_db()
    
    session_maker = get_async_session_maker()
    
    async with session_maker() as session:
        # Check if policies already exist
        from sqlalchemy import select, func
        result = await session.execute(select(func.count(Policy.id)))
        count = result.scalar()
        
        if count > 0:
            print(f"⚠️ Policies table already has {count} records. Skipping seed.")
            print("   To reseed, truncate the policies table first.")
            return
        
        print(f"📝 Adding {len(SAMPLE_POLICIES)} policies...")
        
        for i, policy_data in enumerate(SAMPLE_POLICIES):
            policy = Policy(
                id=str(uuid.uuid4()),
                category=policy_data["category"],
                provider=policy_data["provider"],
                title=policy_data["title"],
                content=policy_data["content"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Generate embedding if pgvector is available
            if PGVECTOR_AVAILABLE:
                try:
                    embedding = await get_embedding(
                        f"{policy_data['title']} {policy_data['content']}"
                    )
                    policy.content_embedding = embedding
                    print(f"   ✅ [{i+1}/{len(SAMPLE_POLICIES)}] {policy_data['title'][:50]}... (with embedding)")
                except Exception as e:
                    print(f"   ⚠️ [{i+1}/{len(SAMPLE_POLICIES)}] {policy_data['title'][:50]}... (no embedding: {e})")
            else:
                print(f"   📄 [{i+1}/{len(SAMPLE_POLICIES)}] {policy_data['title'][:50]}...")
            
            session.add(policy)
        
        await session.commit()
        print(f"\n✅ Successfully seeded {len(SAMPLE_POLICIES)} policies!")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    asyncio.run(seed_policies())