"""
ActionFlow - Standalone Policy Seeder
Mevcut database yapısıyla çalışan bağımsız seed script

Kullanım:
    cd backend
    python app/scripts/seed_policies_standalone.py
"""

import asyncio
import os
import sys

# Backend klasörünü path'e ekle
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from openai import AsyncOpenAI
import uuid


# ═══════════════════════════════════════════════════════════════════
# DATABASE CONNECTION
# ═══════════════════════════════════════════════════════════════════

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/actionflow")

# Sync URL'i async'e çevir
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


# ═══════════════════════════════════════════════════════════════════
# EMBEDDING FUNCTION
# ═══════════════════════════════════════════════════════════════════

async def get_embedding(text: str) -> list:
    """OpenAI embedding oluştur"""
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text.strip().replace("\n", " ")
    )
    return response.data[0].embedding


def format_embedding(embedding: list) -> str:
    """PostgreSQL pgvector formatına çevir"""
    return "[" + ",".join(str(x) for x in embedding) + "]"


# ═══════════════════════════════════════════════════════════════════
# POLICY DATA
# ═══════════════════════════════════════════════════════════════════

POLICIES = [
    # ─────────────── TURKISH AIRLINES ───────────────
    {
        "title": "Turkish Airlines - İptal ve Değişiklik Politikası",
        "category": "cancellation",
        "provider": "Turkish Airlines",
        "content": """
TÜRK HAVA YOLLARI İPTAL VE DEĞİŞİKLİK KURALLARI

1. ESNEK BİLETLER (Business Class, Full Flex Economy)
- Ücretsiz iptal: Uçuştan 24 saat öncesine kadar
- Ücretsiz değişiklik: Sınırsız
- İade süresi: 7-14 iş günü

2. STANDART BİLETLER (Economy Flex)
- İptal ücreti: Bilet bedelinin %25'i
- Değişiklik ücreti: 50-100 EUR + fark
- Son iptal: Uçuştan 4 saat önce

3. PROMOSYONlu BİLETLER (Economy Light, Promo)
- İptal: İade yok, sadece vergiler iade edilir
- Değişiklik: Mümkün değil veya yüksek ücret

4. UÇUŞ İPTALİ (Havayolu kaynaklı)
- Tam iade veya ücretsiz değişiklik hakkı
- Tazminat: EC 261/2004 kapsamında (250-600 EUR)

İletişim: +90 212 444 0 849
        """
    },
    {
        "title": "Turkish Airlines - Cancellation and Change Policy",
        "category": "cancellation",
        "provider": "Turkish Airlines",
        "content": """
TURKISH AIRLINES CANCELLATION AND CHANGE RULES

1. FLEXIBLE TICKETS (Business Class, Full Flex Economy)
- Free cancellation: Up to 24 hours before flight
- Free changes: Unlimited
- Refund time: 7-14 business days

2. STANDARD TICKETS (Economy Flex)
- Cancellation fee: 25% of ticket price
- Change fee: 50-100 EUR + fare difference
- Last cancellation: 4 hours before flight

3. PROMOTIONAL TICKETS (Economy Light, Promo)
- Cancellation: No refund, only taxes refunded
- Changes: Not possible or high fee

4. FLIGHT CANCELLATION (Airline's fault)
- Full refund or free rebooking
- Compensation: Under EC 261/2004 (250-600 EUR)

Contact: +90 212 444 0 849
        """
    },
    {
        "title": "Turkish Airlines - Bagaj Hakkı ve Kuralları",
        "category": "baggage",
        "provider": "Turkish Airlines",
        "content": """
TÜRK HAVA YOLLARI BAGAJ KURALLARI

1. KABİN BAGAJI (Tüm yolcular)
- 1 adet el bagajı: 8 kg, 55x40x23 cm
- 1 adet kişisel eşya: Laptop çantası veya el çantası
- Business Class: 2 adet kabin bagajı (toplam 16 kg)

2. KAYITLI BAGAJ HAKKI

Yurt İçi Uçuşlar:
- Economy Light: 15 kg
- Economy: 20 kg
- Economy Flex: 25 kg
- Business: 32 kg (2 parça)

Yurt Dışı Uçuşlar (Avrupa):
- Economy Light: 20 kg
- Economy: 23 kg
- Economy Flex: 30 kg
- Business: 32 kg (2 parça)

3. FAZLA BAGAJ ÜCRETLERİ
- Yurt içi: Kg başına 3 EUR
- Avrupa: Kg başına 8 EUR
- Uzak mesafe: Kg başına 15 EUR
        """
    },
    {
        "title": "Turkish Airlines - Baggage Allowance and Rules",
        "category": "baggage",
        "provider": "Turkish Airlines",
        "content": """
TURKISH AIRLINES BAGGAGE RULES

1. CABIN BAGGAGE (All passengers)
- 1 carry-on: 8 kg, 55x40x23 cm
- 1 personal item: Laptop bag or handbag
- Business Class: 2 carry-ons (total 16 kg)

2. CHECKED BAGGAGE ALLOWANCE

Domestic Flights:
- Economy Light: 15 kg
- Economy: 20 kg
- Economy Flex: 25 kg
- Business: 32 kg (2 pieces)

International Flights (Europe):
- Economy Light: 20 kg
- Economy: 23 kg
- Economy Flex: 30 kg
- Business: 32 kg (2 pieces)

3. EXCESS BAGGAGE FEES
- Domestic: 3 EUR per kg
- Europe: 8 EUR per kg
- Long haul: 15 EUR per kg
        """
    },
    
    # ─────────────── PEGASUS ───────────────
    {
        "title": "Pegasus Airlines - İptal ve Değişiklik Kuralları",
        "category": "cancellation",
        "provider": "Pegasus Airlines",
        "content": """
PEGASUS HAVA YOLLARI İPTAL VE DEĞİŞİKLİK KURALLARI

1. BASIC PAKET
- İptal: İade yok (sadece vergiler)
- Değişiklik: Mümkün değil
- Koltuk seçimi: Ücretli

2. ESSENTIALS PAKET
- İptal: %50 kesinti ile iade
- Değişiklik: 1 kez ücretsiz (uçuştan 3 gün önce)
- 15 kg bagaj dahil

3. ADVANTAGE PAKET
- İptal: %25 kesinti ile iade
- Değişiklik: Sınırsız ücretsiz
- 20 kg bagaj + koltuk seçimi dahil

4. FLEXPERK (Ek satın alma)
- 99 TL ile değişiklik hakkı
- Uçuştan 3 saat önceye kadar

Online işlem: flypgs.com/manage-booking
Çağrı merkezi: 0888 228 1212
        """
    },
    {
        "title": "Pegasus Airlines - Cancellation and Change Rules",
        "category": "cancellation",
        "provider": "Pegasus Airlines",
        "content": """
PEGASUS AIRLINES CANCELLATION AND CHANGE RULES

1. BASIC PACKAGE
- Cancellation: No refund (taxes only)
- Changes: Not possible
- Seat selection: Paid

2. ESSENTIALS PACKAGE
- Cancellation: 50% deduction refund
- Changes: 1 free change (3 days before flight)
- 15 kg baggage included

3. ADVANTAGE PACKAGE
- Cancellation: 25% deduction refund
- Changes: Unlimited free
- 20 kg baggage + seat selection included

4. FLEXPERK (Add-on)
- Change right for 99 TL
- Up to 3 hours before flight

Online: flypgs.com/manage-booking
Call center: 0888 228 1212
        """
    },
    {
        "title": "Pegasus Airlines - Bagaj Kuralları ve Ücretleri",
        "category": "baggage",
        "provider": "Pegasus Airlines",
        "content": """
PEGASUS BAGAJ KURALLARI VE ÜCRETLERİ

1. KABİN BAGAJI (Tüm paketler)
- 1 adet: 8 kg, 55x40x20 cm
- 1 kişisel eşya: 40x30x15 cm

2. KAYITLI BAGAJ (Paketlere göre)

Basic Paket: Bagaj dahil değil
- Yurt içi: 15 kg = 99 TL / 20 kg = 129 TL
- Yurt dışı: 15 kg = 15 EUR / 20 kg = 20 EUR
- Havalimanında: %50 daha pahalı!

Essentials Paket: 15 kg dahil
Advantage Paket: 20 kg dahil

3. PRO TIP
- Bagajı online önceden alın (havalimanında 2x fiyat!)
- BolBol üyeleri indirimli bagaj alabilir
        """
    },
    {
        "title": "Pegasus Airlines - Baggage Rules and Fees",
        "category": "baggage",
        "provider": "Pegasus Airlines",
        "content": """
PEGASUS BAGGAGE RULES AND FEES

1. CABIN BAGGAGE (All packages)
- 1 piece: 8 kg, 55x40x20 cm
- 1 personal item: 40x30x15 cm

2. CHECKED BAGGAGE (By package)

Basic Package: Not included
- Domestic: 15 kg = 99 TL / 20 kg = 129 TL
- International: 15 kg = 15 EUR / 20 kg = 20 EUR
- At airport: 50% more expensive!

Essentials Package: 15 kg included
Advantage Package: 20 kg included

3. PRO TIP
- Buy baggage online in advance (2x price at airport!)
- BolBol members get discounted baggage
        """
    },
    
    # ─────────────── GENEL POLİTİKALAR ───────────────
    {
        "title": "Genel Otel İptal Politikası",
        "category": "cancellation",
        "provider": "general",
        "content": """
OTEL İPTAL POLİTİKASI (GENEL KURALLAR)

1. ÜCRETSİZ İPTAL
- Çoğu otel: Check-in'den 24-48 saat önce ücretsiz
- Booking.com "Ücretsiz iptal" ibareli: Belirtilen tarihe kadar

2. İPTAL ÜCRETLİ DURUMLAR
- Son dakika iptal: 1 gecelik ücret
- No-show (gelmeme): Tam ücret
- İade edilemez rezervasyon: Hiçbir iade yok

3. ÖDEME TİPİNE GÖRE
- Otelde ödeme: İptal daha esnek
- Ön ödemeli: İade zor veya yok

4. TAVSİYELER
- Rezervasyon yaparken iptal şartlarını okuyun
- Ücretsiz iptal tarihi takvime not edin
        """
    },
    {
        "title": "General Hotel Cancellation Policy",
        "category": "cancellation",
        "provider": "general",
        "content": """
HOTEL CANCELLATION POLICY (GENERAL RULES)

1. FREE CANCELLATION
- Most hotels: Free up to 24-48 hours before check-in
- Booking.com "Free cancellation": Until specified date

2. CANCELLATION WITH FEE
- Last minute cancellation: 1 night charge
- No-show: Full charge
- Non-refundable booking: No refund

3. BY PAYMENT TYPE
- Pay at hotel: More flexible cancellation
- Prepaid: Refund difficult or none

4. RECOMMENDATIONS
- Read cancellation terms when booking
- Note free cancellation date in calendar
        """
    },
    {
        "title": "Uçuş Rötar ve İptal Hakları (AB/EC 261)",
        "category": "refund",
        "provider": "general",
        "content": """
YOLCU HAKLARI - EC 261/2004 (AB DÜZENLEMESİ)

1. UÇUŞ İPTALİ TAZMİNATI
- 1500 km'ye kadar: 250 EUR
- 1500-3500 km: 400 EUR
- 3500 km üzeri: 600 EUR

2. RÖTAR TAZMİNATI
- 3+ saat rötar: İptal ile aynı tazminat
- 5+ saat rötar: Tam iade hakkı

3. BEKLEME SÜRESİNCE HAKLAR
- 2+ saat: Yemek, içecek
- 4+ saat: Otel + transfer

4. BAGAJ GECİKMESİ
- Günlük ihtiyaçlar: Havayolu karşılar
- Max tazminat: ~1400 EUR
        """
    },
    {
        "title": "Flight Delay and Cancellation Rights (EU/EC 261)",
        "category": "refund",
        "provider": "general",
        "content": """
PASSENGER RIGHTS - EC 261/2004 (EU REGULATION)

1. FLIGHT CANCELLATION COMPENSATION
- Up to 1500 km: 250 EUR
- 1500-3500 km: 400 EUR
- Over 3500 km: 600 EUR

2. DELAY COMPENSATION
- 3+ hour delay: Same compensation as cancellation
- 5+ hour delay: Full refund right

3. RIGHTS DURING WAITING
- 2+ hours: Food, drinks
- 4+ hours: Hotel + transfer

4. BAGGAGE DELAY
- Daily necessities: Airline covers
- Max compensation: ~1400 EUR
        """
    },
    {
        "title": "Check-in Kuralları ve Saatleri",
        "category": "check-in",
        "provider": "general",
        "content": """
CHECK-IN KURALLARI VE SAATLERİ

1. ONLINE CHECK-IN
- Ne zaman: Uçuştan 24-48 saat önce açılır
- Kapanış: Uçuştan 1-3 saat önce

THY: 24 saat önce - 90 dakika önce
Pegasus: 24 saat önce - 60 dakika önce

2. HAVALIMANINDA CHECK-IN
- Açılış: Uçuştan 3 saat önce
- Kapanış: Yurt içi 45dk, Yurt dışı 60dk önce

3. GATE KAPANIŞ
- Boarding: Uçuştan 30-45 dakika önce başlar
- Gate kapanış: Uçuştan 15-20 dakika önce

4. TAVSİYELER
- Yurt içi: 1.5-2 saat önce havalimanında olun
- Yurt dışı: 2.5-3 saat önce
        """
    },
    {
        "title": "Check-in Rules and Times",
        "category": "check-in",
        "provider": "general",
        "content": """
CHECK-IN RULES AND TIMES

1. ONLINE CHECK-IN
- When: Opens 24-48 hours before flight
- Closes: 1-3 hours before flight

Turkish Airlines: 24h before - 90 min before
Pegasus: 24h before - 60 min before

2. AIRPORT CHECK-IN
- Opens: 3 hours before flight
- Closes: Domestic 45min, International 60min before

3. GATE CLOSURE
- Boarding: Starts 30-45 minutes before flight
- Gate closes: 15-20 minutes before flight

4. RECOMMENDATIONS
- Domestic: Be at airport 1.5-2 hours before
- International: 2.5-3 hours before
        """
    }
]


# ═══════════════════════════════════════════════════════════════════
# SEED FUNCTION
# ═══════════════════════════════════════════════════════════════════

async def seed_policies():
    """Politikaları veritabanına ekle"""
    
    print("🔌 Connecting to database...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Mevcut politikaları temizle (opsiyonel)
        print("🗑️  Clearing existing policies...")
        await conn.execute(text("DELETE FROM policies"))
    
    async with engine.connect() as conn:
        print(f"🌱 Seeding {len(POLICIES)} policies...")
        
        for i, policy in enumerate(POLICIES, 1):
            policy_id = f"policy-{uuid.uuid4().hex[:8]}"
            
            # Embedding oluştur
            print(f"   [{i}/{len(POLICIES)}] {policy['title'][:50]}...")
            embedding_text = f"{policy['title']}. {policy['content']}"
            
            try:
                embedding = await get_embedding(embedding_text)
                embedding_str = format_embedding(embedding)
            except Exception as e:
                print(f"   ⚠️  Embedding error: {e}")
                continue
            
            # Veritabanına ekle - raw SQL with proper escaping
            sql = text("""
                INSERT INTO policies (
                    id, title, content, category, provider,
                    content_embedding, created_at, updated_at
                ) VALUES (
                    :id, :title, :content, :category, :provider,
                    cast(:embedding as vector), NOW(), NOW()
                )
            """)
            
            await conn.execute(sql, {
                "id": policy_id,
                "title": policy["title"],
                "content": policy["content"].strip(),
                "category": policy["category"],
                "provider": policy["provider"],
                "embedding": embedding_str
            })
        
        await conn.commit()
        print(f"✅ Seeded {len(POLICIES)} policies successfully!")
    
    await engine.dispose()


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("ActionFlow - Policy Seeder")
    print("=" * 50)
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment!")
        print("   Set it in .env file or export it.")
        sys.exit(1)
    
    print(f"📦 Database: {DATABASE_URL[:50]}...")
    print(f"🔑 OpenAI API Key: {os.getenv('OPENAI_API_KEY')[:20]}...")
    print()
    
    asyncio.run(seed_policies())