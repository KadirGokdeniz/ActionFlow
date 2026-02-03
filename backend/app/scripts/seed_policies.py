"""
ActionFlow - Seed Policies
THY, Pegasus ve genel seyahat politikaları (Türkçe & İngilizce)

Kullanım:
    python -m scripts.seed_policies
    
    veya
    
    from scripts.seed_policies import seed_all_policies
    await seed_all_policies(db_session)
"""

import asyncio
import logging
from typing import List, Dict, Any

logger = logging.getLogger("ActionFlow-SeedPolicies")


# ═══════════════════════════════════════════════════════════════════
# TURKISH AIRLINES (THY) POLİTİKALARI
# ═══════════════════════════════════════════════════════════════════

THY_POLICIES = [
    # İptal Politikaları
    {
        "title": "Turkish Airlines - İptal ve Değişiklik Politikası",
        "title_en": "Turkish Airlines - Cancellation and Change Policy",
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
- Açık bilete çevirme: Mümkün değil

4. HASTALIK / ÖLÜM DURUMU
- Tam iade mümkün (doktor raporu/ölüm belgesi ile)
- 72 saat içinde başvuru gerekli

5. UÇUŞ İPTALİ (Havayolu kaynaklı)
- Tam iade veya ücretsiz değişiklik hakkı
- Tazminat: EC 261/2004 kapsamında (250-600 EUR)

İletişim: +90 212 444 0 849
Online işlem: turkishairlines.com/manage-booking
        """,
        "content_en": """
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
- Open ticket: Not possible

4. ILLNESS / DEATH
- Full refund possible (with doctor's report/death certificate)
- Application within 72 hours required

5. FLIGHT CANCELLATION (Airline's fault)
- Full refund or free rebooking
- Compensation: Under EC 261/2004 (250-600 EUR)

Contact: +90 212 444 0 849
Online: turkishairlines.com/manage-booking
        """,
        "source_url": "https://www.turkishairlines.com/en-int/any-questions/cancellation-and-refund/"
    },
    
    # Bagaj Politikası
    {
        "title": "Turkish Airlines - Bagaj Hakkı ve Kuralları",
        "title_en": "Turkish Airlines - Baggage Allowance and Rules",
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

Amerika Uçuşları:
- Economy: 2 x 23 kg
- Business: 2 x 32 kg

3. FAZLA BAGAJ ÜCRETLERİ
- Yurt içi: Kg başına 3 EUR
- Avrupa: Kg başına 8 EUR
- Uzak mesafe: Kg başına 15 EUR
- Ekstra parça: 60-150 EUR

4. ÖZEL BAGAJ
- Spor ekipmanı: 30-75 EUR
- Müzik aleti: Kabin veya ek koltuk
- Evcil hayvan: 35-200 EUR (kabin/kargo)

5. YASAK MADDELER
- Pil ve powerbank: Sadece kabin (max 100Wh)
- Sıvılar: 100ml, şeffaf poşet
- Kesici aletler: Kayıtlı bagajda

Miles&Smiles üyeleri ek bagaj hakkından yararlanır.
        """,
        "content_en": """
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

America Flights:
- Economy: 2 x 23 kg
- Business: 2 x 32 kg

3. EXCESS BAGGAGE FEES
- Domestic: 3 EUR per kg
- Europe: 8 EUR per kg
- Long haul: 15 EUR per kg
- Extra piece: 60-150 EUR

4. SPECIAL BAGGAGE
- Sports equipment: 30-75 EUR
- Musical instrument: Cabin or extra seat
- Pets: 35-200 EUR (cabin/cargo)

5. PROHIBITED ITEMS
- Batteries and powerbanks: Cabin only (max 100Wh)
- Liquids: 100ml, clear bag
- Sharp objects: Checked baggage only

Miles&Smiles members get extra baggage allowance.
        """,
        "source_url": "https://www.turkishairlines.com/en-int/any-questions/baggage/"
    },
    
    # İade Politikası
    {
        "title": "Turkish Airlines - İade Süreci ve Süreleri",
        "title_en": "Turkish Airlines - Refund Process and Timeline",
        "category": "refund",
        "provider": "Turkish Airlines",
        "content": """
TÜRK HAVA YOLLARI İADE SÜRECİ

1. İADE SÜRELERİ
- Kredi kartı: 7-14 iş günü
- Banka havalesi: 14-21 iş günü
- Seyahat acentası: Acenta üzerinden (30 güne kadar)

2. İADE BAŞVURUSU
- Online: turkishairlines.com → Rezervasyonlarım
- Çağrı merkezi: +90 212 444 0 849
- Havalimanı: THY satış ofisleri

3. İADE EDİLEN TUTARLAR
- Bilet ücreti (iptal şartlarına göre)
- Vergiler ve harçlar (tam iade)
- Ek hizmetler (koltuk seçimi, bagaj - iade yok)

4. KESINTILER
- İptal ücreti (bilet tipine göre)
- İşlem ücreti: 25 EUR (bazı kanallar)
- Kur farkı (yabancı para ile alımlarda)

5. AÇIK BİLET
- 1 yıl geçerli
- Fark ödemesi gerekebilir
- Rota değişikliği ücrete tabi

6. VOUCHER SEÇENEĞİ
- Bilet bedeli + %10 bonus
- 1 yıl geçerli
- Tüm THY uçuşlarında kullanılabilir

İade durumu takibi: turkishairlines.com/refund-status
        """,
        "content_en": """
TURKISH AIRLINES REFUND PROCESS

1. REFUND TIMELINE
- Credit card: 7-14 business days
- Bank transfer: 14-21 business days
- Travel agency: Through agency (up to 30 days)

2. REFUND APPLICATION
- Online: turkishairlines.com → My Bookings
- Call center: +90 212 444 0 849
- Airport: THY sales offices

3. REFUNDED AMOUNTS
- Ticket price (according to cancellation terms)
- Taxes and fees (full refund)
- Ancillaries (seat selection, baggage - no refund)

4. DEDUCTIONS
- Cancellation fee (depends on ticket type)
- Processing fee: 25 EUR (some channels)
- Exchange rate difference (foreign currency purchases)

5. OPEN TICKET
- Valid for 1 year
- Fare difference may apply
- Route change subject to fee

6. VOUCHER OPTION
- Ticket value + 10% bonus
- Valid for 1 year
- Can be used on all THY flights

Refund status tracking: turkishairlines.com/refund-status
        """
    }
]


# ═══════════════════════════════════════════════════════════════════
# PEGASUS POLİTİKALARI
# ═══════════════════════════════════════════════════════════════════

PEGASUS_POLICIES = [
    {
        "title": "Pegasus Airlines - İptal ve Değişiklik Kuralları",
        "title_en": "Pegasus Airlines - Cancellation and Change Rules",
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

4. DEĞİŞİKLİK ÜCRETLERİ (Basic için)
- Yurt içi: 50 TL + fark
- Yurt dışı: 25 EUR + fark
- İsim düzeltme: 50 TL/EUR

5. SON DAKİKA DEĞİŞİKLİK
- Uçuştan 3 saat önceye kadar mümkün
- Ek ücret uygulanabilir

6. FLEXPERK (Ek satın alma)
- 99 TL ile değişiklik hakkı
- Uçuştan 3 saat önceye kadar
- Bilet alırken eklenmeli

Online işlem: flypgs.com/manage-booking
Çağrı merkezi: 0888 228 1212
        """,
        "content_en": """
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

4. CHANGE FEES (For Basic)
- Domestic: 50 TL + difference
- International: 25 EUR + difference
- Name correction: 50 TL/EUR

5. LAST MINUTE CHANGES
- Possible up to 3 hours before flight
- Additional fee may apply

6. FLEXPERK (Add-on)
- Change right for 99 TL
- Up to 3 hours before flight
- Must be added at booking

Online: flypgs.com/manage-booking
Call center: 0888 228 1212
        """,
        "source_url": "https://www.flypgs.com/en/pegasus-baggage-rules"
    },
    
    {
        "title": "Pegasus Airlines - Bagaj Kuralları ve Ücretleri",
        "title_en": "Pegasus Airlines - Baggage Rules and Fees",
        "category": "baggage",
        "provider": "Pegasus Airlines",
        "content": """
PEGASUS BAGAJ KURALLARI VE ÜCRETLERİ

1. KABİN BAGAJI (Tüm paketler)
- 1 adet: 8 kg, 55x40x20 cm
- 1 kişisel eşya: 40x30x15 cm
- Toplam: 8 kg

2. KAYITLI BAGAJ (Paketlere göre)

Basic Paket: Bagaj dahil değil
- Yurt içi: 15 kg = 99 TL / 20 kg = 129 TL
- Yurt dışı: 15 kg = 15 EUR / 20 kg = 20 EUR
- Havalimanında: %50 daha pahalı!

Essentials Paket: 15 kg dahil
Advantage Paket: 20 kg dahil

3. FAZLA BAGAJ
- Online önceden: 5 TL/kg (yurt içi)
- Havalimanında: 10 TL/kg (yurt içi)
- Yurt dışı: 3-8 EUR/kg

4. EK PARÇA BAGAJ
- 2. parça: 79-149 TL / 20-35 EUR
- 3. parça: 129-199 TL / 30-50 EUR

5. ÖZEL BAGAJ
- Kayak/Snowboard: 30 EUR
- Golf: 30 EUR
- Bisiklet: 40 EUR
- Sörf tahtası: 50 EUR
- Evcil hayvan (kabin): 25-50 EUR

6. PRO TIP
- Bagajı online önceden alın (havalimanında 2x fiyat!)
- BolBol üyeleri indirimli bagaj alabilir
- Aile paketi: 30 kg paylaşımlı

Bagaj hesaplama: flypgs.com/baggage-calculator
        """,
        "content_en": """
PEGASUS BAGGAGE RULES AND FEES

1. CABIN BAGGAGE (All packages)
- 1 piece: 8 kg, 55x40x20 cm
- 1 personal item: 40x30x15 cm
- Total: 8 kg

2. CHECKED BAGGAGE (By package)

Basic Package: Not included
- Domestic: 15 kg = 99 TL / 20 kg = 129 TL
- International: 15 kg = 15 EUR / 20 kg = 20 EUR
- At airport: 50% more expensive!

Essentials Package: 15 kg included
Advantage Package: 20 kg included

3. EXCESS BAGGAGE
- Online advance: 5 TL/kg (domestic)
- At airport: 10 TL/kg (domestic)
- International: 3-8 EUR/kg

4. EXTRA PIECE
- 2nd piece: 79-149 TL / 20-35 EUR
- 3rd piece: 129-199 TL / 30-50 EUR

5. SPECIAL BAGGAGE
- Ski/Snowboard: 30 EUR
- Golf: 30 EUR
- Bicycle: 40 EUR
- Surfboard: 50 EUR
- Pet (cabin): 25-50 EUR

6. PRO TIP
- Buy baggage online in advance (2x price at airport!)
- BolBol members get discounted baggage
- Family package: 30 kg shared

Baggage calculator: flypgs.com/baggage-calculator
        """,
        "source_url": "https://www.flypgs.com/en/pegasus-baggage-rules"
    }
]


# ═══════════════════════════════════════════════════════════════════
# GENEL POLİTİKALAR
# ═══════════════════════════════════════════════════════════════════

GENERAL_POLICIES = [
    {
        "title": "Genel Otel İptal Politikası",
        "title_en": "General Hotel Cancellation Policy",
        "category": "cancellation",
        "provider": "general",
        "content": """
OTEL İPTAL POLİTİKASI (GENEL KURALLAR)

1. ÜCRETSİZ İPTAL
- Çoğu otel: Check-in'den 24-48 saat önce ücretsiz
- Booking.com "Ücretsiz iptal" ibareli: Belirtilen tarihe kadar
- Expedia: Genellikle 2-3 gün öncesine kadar

2. İPTAL ÜCRETLİ DURUMLAR
- Son dakika iptal: 1 gecelik ücret
- No-show (gelmeme): Tam ücret
- İade edilemez rezervasyon: Hiçbir iade yok

3. ÖZEL DÖNEMLER
- Yılbaşı, bayram: Daha katı kurallar
- Fuar dönemleri: İptal ücreti yüksek
- Sezon: Daha uzun iptal süresi

4. ÖDEME TİPİNE GÖRE
- Otelde ödeme: İptal daha esnek
- Ön ödemeli: İade zor veya yok
- Kısmi ön ödeme: Ön ödeme kaybedilebilir

5. NASIL İPTAL EDİLİR?
- Online: Rezervasyon sitesi üzerinden
- Telefon: Otel veya site müşteri hizmetleri
- E-posta: Onay numarası ile

6. TAVSİYELER
- Rezervasyon yaparken iptal şartlarını okuyun
- Ücretsiz iptal tarihi takvime not edin
- Seyahat sigortası değerlendirin
        """,
        "content_en": """
HOTEL CANCELLATION POLICY (GENERAL RULES)

1. FREE CANCELLATION
- Most hotels: Free up to 24-48 hours before check-in
- Booking.com "Free cancellation": Until specified date
- Expedia: Usually up to 2-3 days before

2. CANCELLATION WITH FEE
- Last minute cancellation: 1 night charge
- No-show: Full charge
- Non-refundable booking: No refund

3. SPECIAL PERIODS
- New Year, holidays: Stricter rules
- Fair periods: Higher cancellation fee
- Peak season: Longer cancellation notice

4. BY PAYMENT TYPE
- Pay at hotel: More flexible cancellation
- Prepaid: Refund difficult or none
- Partial prepayment: Prepayment may be lost

5. HOW TO CANCEL?
- Online: Through booking website
- Phone: Hotel or website customer service
- Email: With confirmation number

6. RECOMMENDATIONS
- Read cancellation terms when booking
- Note free cancellation date in calendar
- Consider travel insurance
        """
    },
    
    {
        "title": "Uçuş Rötar ve İptal Hakları (AB/EC 261)",
        "title_en": "Flight Delay and Cancellation Rights (EU/EC 261)",
        "category": "refund",
        "provider": "general",
        "content": """
YOLCU HAKLARI - EC 261/2004 (AB DÜZENLEMESİ)

Bu haklar AB kalkışlı veya AB havayolu ile AB varışlı uçuşlarda geçerlidir.

1. UÇUŞ İPTALİ TAZMİNATI
- 1500 km'ye kadar: 250 EUR
- 1500-3500 km: 400 EUR
- 3500 km üzeri: 600 EUR

Şartlar:
- 14 günden az önce bildirim
- Olağanüstü koşullar (hava, grev) hariç

2. RÖTAR TAZMİNATI
- 3+ saat rötar: İptal ile aynı tazminat
- 5+ saat rötar: Tam iade hakkı

3. BEKLEME SÜRESİNCE HAKLAR
- 2+ saat: Yemek, içecek
- 4+ saat: Otel + transfer
- Ücretsiz iletişim (2 telefon/e-posta)

4. OVERBOOKING (Fazla satış)
- Gönüllü: Havayolu teklifi + tazminat
- Zorunlu: Tam tazminat + alternatif uçuş

5. BAGAJ GECİKMESİ
- Günlük ihtiyaçlar: Havayolu karşılar
- Max tazminat: ~1400 EUR (Montreal Sözleşmesi)
- 21 gün sonra kayıp sayılır

6. BAŞVURU
- Havayoluna direkt başvuru
- 3 yıl içinde talep edilmeli
- Red edilirse: Tüketici hakları kurumları

Türkiye'de: SHGM (shgm.gov.tr)
AB'de: Ulusal uygulama kurumları
        """,
        "content_en": """
PASSENGER RIGHTS - EC 261/2004 (EU REGULATION)

These rights apply to EU departure or EU airline flights arriving in EU.

1. FLIGHT CANCELLATION COMPENSATION
- Up to 1500 km: 250 EUR
- 1500-3500 km: 400 EUR
- Over 3500 km: 600 EUR

Conditions:
- Less than 14 days notice
- Extraordinary circumstances (weather, strike) excluded

2. DELAY COMPENSATION
- 3+ hour delay: Same compensation as cancellation
- 5+ hour delay: Full refund right

3. RIGHTS DURING WAITING
- 2+ hours: Food, drinks
- 4+ hours: Hotel + transfer
- Free communication (2 calls/emails)

4. OVERBOOKING
- Voluntary: Airline offer + compensation
- Involuntary: Full compensation + alternative flight

5. BAGGAGE DELAY
- Daily necessities: Airline covers
- Max compensation: ~1400 EUR (Montreal Convention)
- After 21 days: Considered lost

6. APPLICATION
- Apply directly to airline
- Claim within 3 years
- If rejected: Consumer rights organizations

In Turkey: SHGM (shgm.gov.tr)
In EU: National enforcement bodies
        """
    },
    
    {
        "title": "Check-in Kuralları ve Saatleri",
        "title_en": "Check-in Rules and Times",
        "category": "check-in",
        "provider": "general",
        "content": """
CHECK-IN KURALLARI VE SAATLERİ

1. ONLINE CHECK-IN
- Ne zaman: Uçuştan 24-48 saat önce açılır
- Kapanış: Uçuştan 1-3 saat önce
- Avantaj: Sıra beklemeden, koltuk seçimi

THY: 24 saat önce - 90 dakika önce
Pegasus: 24 saat önce - 60 dakika önce
Avrupa havayolları: 24-48 saat önce

2. HAVALIMANINDA CHECK-IN
- Açılış: Uçuştan 3 saat önce (genel)
- Kapanış: Yurt içi 45dk, Yurt dışı 60dk önce
- Yoğun saatlerde erken gelin!

3. KIOSK CHECK-IN
- Ortalama süre: 2-5 dakika
- Bagaj etiketi yazdırabilirsiniz
- Sadece standart işlemler için

4. BAGAJ BIRAKMA (Bag Drop)
- Online check-in yaptıysanız direkt bagaj bırakma
- Ayrı sıra, genellikle daha hızlı
- Kapanış: Uçuştan 45-60 dk önce

5. GATE KAPANIŞ
- Boarding: Uçuştan 30-45 dakika önce başlar
- Gate kapanış: Uçuştan 15-20 dakika önce
- Son çağrı kaçırılırsa: Uçuşa alınmayabilirsiniz

6. GEREKLİ BELGELER
- Yurt içi: Kimlik veya pasaport
- Yurt dışı: Pasaport (min 6 ay geçerli)
- Vize: Hedef ülke gereksinimlerine göre
- PNR/Rezervasyon kodu

7. TAVSİYELER
- Yurt içi: 1.5-2 saat önce havalimanında olun
- Yurt dışı: 2.5-3 saat önce
- Transfer: Min 1.5-2 saat ara uçuş süresi
        """,
        "content_en": """
CHECK-IN RULES AND TIMES

1. ONLINE CHECK-IN
- When: Opens 24-48 hours before flight
- Closes: 1-3 hours before flight
- Advantage: Skip queues, seat selection

Turkish Airlines: 24h before - 90 min before
Pegasus: 24h before - 60 min before
European airlines: 24-48h before

2. AIRPORT CHECK-IN
- Opens: 3 hours before flight (general)
- Closes: Domestic 45min, International 60min before
- Arrive early during peak hours!

3. KIOSK CHECK-IN
- Average time: 2-5 minutes
- Can print baggage tags
- For standard transactions only

4. BAG DROP
- If online check-in done, go straight to bag drop
- Separate queue, usually faster
- Closes: 45-60 min before flight

5. GATE CLOSURE
- Boarding: Starts 30-45 minutes before flight
- Gate closes: 15-20 minutes before flight
- Miss last call: May not be allowed on flight

6. REQUIRED DOCUMENTS
- Domestic: ID or passport
- International: Passport (min 6 months valid)
- Visa: According to destination country
- PNR/Booking code

7. RECOMMENDATIONS
- Domestic: Be at airport 1.5-2 hours before
- International: 2.5-3 hours before
- Transfer: Min 1.5-2 hours between flights
        """
    }
]


# ═══════════════════════════════════════════════════════════════════
# SEED FUNCTION
# ═══════════════════════════════════════════════════════════════════

def get_all_policies() -> List[Dict[str, Any]]:
    """Tüm politikaları birleştir"""
    all_policies = []
    
    # THY
    for p in THY_POLICIES:
        all_policies.append({
            "title": p["title"],
            "content": p["content"].strip(),
            "category": p["category"],
            "provider": p["provider"],
            "source_url": p.get("source_url")
        })
        # İngilizce versiyon
        if "title_en" in p and "content_en" in p:
            all_policies.append({
                "title": p["title_en"],
                "content": p["content_en"].strip(),
                "category": p["category"],
                "provider": p["provider"],
                "source_url": p.get("source_url")
            })
    
    # Pegasus
    for p in PEGASUS_POLICIES:
        all_policies.append({
            "title": p["title"],
            "content": p["content"].strip(),
            "category": p["category"],
            "provider": p["provider"],
            "source_url": p.get("source_url")
        })
        if "title_en" in p and "content_en" in p:
            all_policies.append({
                "title": p["title_en"],
                "content": p["content_en"].strip(),
                "category": p["category"],
                "provider": p["provider"],
                "source_url": p.get("source_url")
            })
    
    # General
    for p in GENERAL_POLICIES:
        all_policies.append({
            "title": p["title"],
            "content": p["content"].strip(),
            "category": p["category"],
            "provider": p["provider"],
            "source_url": p.get("source_url")
        })
        if "title_en" in p and "content_en" in p:
            all_policies.append({
                "title": p["title_en"],
                "content": p["content_en"].strip(),
                "category": p["category"],
                "provider": p["provider"],
                "source_url": p.get("source_url")
            })
    
    return all_policies


async def seed_all_policies(db_session):
    """
    Tüm politikaları veritabanına ekle
    
    Args:
        db_session: AsyncSession
    """
    from app.services.policy_service import PolicyService
    
    logger.info("Starting policy seeding...")
    
    service = PolicyService(db_session)
    policies = get_all_policies()
    
    created_ids = await service.bulk_create(policies)
    
    logger.info(f"Seeded {len(created_ids)} policies")
    return created_ids


# ═══════════════════════════════════════════════════════════════════
# CLI ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════

async def main():
    """CLI entrypoint"""
    import os
    import sys
    
    # Add project root to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from app.core.database import get_db_session
    
    print("🌱 Seeding policies...")
    print(f"   Total policies to create: {len(get_all_policies())}")
    
    async with get_db_session() as db:
        ids = await seed_all_policies(db)
        print(f"✅ Created {len(ids)} policies")


if __name__ == "__main__":
    asyncio.run(main())