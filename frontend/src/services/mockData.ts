import type { Conversation, Message, FlightInfo, HotelInfo, BookingInfo } from '@/types';

// Helper to generate IDs
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Mock flight data
export const mockFlights: FlightInfo[] = [
  {
    id: 'flight-1',
    airline: 'Turkish Airlines',
    airlineLogo: 'TK',
    flightNumber: 'TK1951',
    origin: { code: 'IST', city: 'İstanbul', time: '08:30' },
    destination: { code: 'CDG', city: 'Paris', time: '11:45' },
    duration: '3s 15dk',
    stops: 0,
    price: 4250,
    currency: 'TRY',
    class: 'economy',
  },
  {
    id: 'flight-2',
    airline: 'Air France',
    airlineLogo: 'AF',
    flightNumber: 'AF1391',
    origin: { code: 'IST', city: 'İstanbul', time: '14:20' },
    destination: { code: 'CDG', city: 'Paris', time: '17:30' },
    duration: '3s 10dk',
    stops: 0,
    price: 3890,
    currency: 'TRY',
    class: 'economy',
  },
  {
    id: 'flight-3',
    airline: 'Pegasus',
    airlineLogo: 'PC',
    flightNumber: 'PC1234',
    origin: { code: 'SAW', city: 'İstanbul Sabiha', time: '06:15' },
    destination: { code: 'ORY', city: 'Paris Orly', time: '09:45' },
    duration: '3s 30dk',
    stops: 0,
    price: 2450,
    currency: 'TRY',
    class: 'economy',
  },
];

// Mock hotel data
export const mockHotels: HotelInfo[] = [
  {
    id: 'hotel-1',
    name: 'Hôtel Plaza Athénée',
    location: 'Champs-Élysées, Paris',
    rating: 5,
    reviewCount: 1247,
    pricePerNight: 15000,
    currency: 'TRY',
    amenities: ['Spa', 'Restaurant', 'Concierge', 'WiFi'],
  },
  {
    id: 'hotel-2',
    name: 'Mercure Paris Centre',
    location: 'Le Marais, Paris',
    rating: 4,
    reviewCount: 892,
    pricePerNight: 4500,
    currency: 'TRY',
    amenities: ['Restaurant', 'Bar', 'WiFi', 'Fitness'],
  },
  {
    id: 'hotel-3',
    name: 'Ibis Styles Montmartre',
    location: 'Montmartre, Paris',
    rating: 3,
    reviewCount: 2103,
    pricePerNight: 2200,
    currency: 'TRY',
    amenities: ['WiFi', 'Bar', 'Breakfast'],
  },
];

// Mock booking data
export const mockBookings: BookingInfo[] = [
  {
    id: 'booking-1',
    referenceNumber: 'AF-2024-78932',
    type: 'flight',
    status: 'confirmed',
    details: 'İstanbul (IST) → Paris (CDG), 22 Ocak 2026',
    date: '2026-01-22',
    price: 4250,
    currency: 'TRY',
  },
  {
    id: 'booking-2',
    referenceNumber: 'HT-2024-45621',
    type: 'hotel',
    status: 'pending',
    details: 'Mercure Paris Centre, 22-27 Ocak 2026',
    date: '2026-01-22',
    price: 22500,
    currency: 'TRY',
  },
];

// AI Response templates
const aiResponses: Record<string, string[]> = {
  greeting: [
    'Merhaba! 👋 ActionFlow seyahat asistanınız olarak size nasıl yardımcı olabilirim?\n\n✈️ Uçuş araması\n🏨 Otel rezervasyonu\n📋 Rezervasyon yönetimi\n❓ Seyahat politikaları',
    "Hello! 👋 I'm your ActionFlow travel assistant. How can I help you today?\n\n✈️ Flight search\n🏨 Hotel booking\n📋 Booking management\n❓ Travel policies",
  ],
  paris_interest: [
    "Paris harika bir seçim! 🇫🇷\n\nSize en iyi seçenekleri sunabilmem için birkaç bilgiye ihtiyacım var:\n\n- **Ne zaman** gitmek istiyorsunuz?\n- **Kaç gün** kalmayı planlıyorsunuz?\n- **Kaç kişi** seyahat edecek?\n\nBu bilgileri paylaşır mısınız?",
  ],
  travel_details: [
    "Harika! Seyahat planınız hazır:\n\n📋 **Seyahat Planınız**\n━━━━━━━━━━━━━━━━━━━━━\n🛫 İstanbul (IST) → Paris (CDG)\n📅 22 Ocak 2026 - 27 Ocak 2026\n👥 2 Yolcu\n━━━━━━━━━━━━━━━━━━━━━\n\n✅ Uçuş ve otel aramalarına başlayayım mı?",
  ],
  flight_search: [
    "Size uygun uçuş seçeneklerini buldum! ✈️\n\nİşte İstanbul - Paris güzergahı için en iyi 3 seçenek:\n\n1. **Turkish Airlines TK1951**\n   08:30 → 11:45 (3s 15dk) | Direkt\n   💰 4.250 TL\n\n2. **Air France AF1391**\n   14:20 → 17:30 (3s 10dk) | Direkt\n   💰 3.890 TL\n\n3. **Pegasus PC1234**\n   06:15 → 09:45 (3s 30dk) | Direkt\n   💰 2.450 TL\n\nHangi uçuşu seçmek istersiniz?",
  ],
  hotel_search: [
    "Paris'te kalabileceğiniz oteller 🏨\n\n1. **Hôtel Plaza Athénée** ⭐⭐⭐⭐⭐\n   📍 Champs-Élysées | 💰 15.000 TL/gece\n   Spa, Restaurant, Concierge\n\n2. **Mercure Paris Centre** ⭐⭐⭐⭐\n   📍 Le Marais | 💰 4.500 TL/gece\n   Restaurant, Bar, Fitness\n\n3. **Ibis Styles Montmartre** ⭐⭐⭐\n   📍 Montmartre | 💰 2.200 TL/gece\n   WiFi, Kahvaltı dahil\n\nHangi oteli tercih edersiniz?",
  ],
  booking_confirmed: [
    "🎉 Rezervasyonunuz onaylandı!\n\n📋 **Rezervasyon Detayları**\n━━━━━━━━━━━━━━━━━━━━━\n🔖 Referans: **AF-2024-78932**\n✈️ Turkish Airlines TK1951\n📅 22 Ocak 2026\n⏰ 08:30 - 11:45\n👥 2 Yolcu\n💰 8.500 TL\n━━━━━━━━━━━━━━━━━━━━━\n\n📧 Onay e-postası gönderildi!\n\nBaşka bir konuda yardımcı olabilir miyim?",
  ],
  cancel_inquiry: [
    "İptal işlemi hakkında yardımcı olabilirim. 📋\n\n**İptal Politikamız:**\n- Kalkıştan 24+ saat önce: **Tam iade**\n- Kalkıştan 12-24 saat önce: **%50 iade**\n- Kalkıştan 12 saatten az: **İade yok**\n\nHangi rezervasyonu iptal etmek istiyorsunuz? Lütfen rezervasyon numaranızı paylaşın.",
  ],
  refund_status: [
    "İade durumunuzu kontrol ediyorum... 💰\n\n**İade Bilgisi**\n━━━━━━━━━━━━━━━━━━━━━\n🔖 Referans: AF-2024-78932\n💳 İade Tutarı: 4.250 TL\n📊 Durum: **İşleniyor**\n⏱️ Tahmini Süre: 3-5 iş günü\n━━━━━━━━━━━━━━━━━━━━━\n\nİade hesabınıza yatırıldığında SMS ile bilgilendirileceksiniz.",
  ],
  fallback: [
    "Anladım! Size bu konuda yardımcı olabilirim. Lütfen biraz daha detay verir misiniz?\n\nYa da şu seçeneklerden birini kullanabilirsiniz:\n- ✈️ Uçuş Ara\n- 🏨 Otel Bul\n- 📋 Rezervasyonlarım\n- ❓ Politikalar",
  ],
};

// Intent detection (simple keyword matching for mock)
function detectIntent(message: string): string {
  const lowerMessage = message.toLowerCase();

  if (lowerMessage.includes('merhaba') || lowerMessage.includes('selam') || lowerMessage.includes('hello') || lowerMessage.includes('hi')) {
    return 'greeting';
  }
  if (lowerMessage.includes('paris')) {
    return 'paris_interest';
  }
  if (lowerMessage.includes('yarın') || lowerMessage.includes('gün') || lowerMessage.includes('kişi') || lowerMessage.includes('kişiyiz')) {
    return 'travel_details';
  }
  if (lowerMessage.includes('uçuş') || lowerMessage.includes('flight') || lowerMessage.includes('uçak')) {
    return 'flight_search';
  }
  if (lowerMessage.includes('otel') || lowerMessage.includes('hotel') || lowerMessage.includes('konaklama')) {
    return 'hotel_search';
  }
  if (lowerMessage.includes('iptal') || lowerMessage.includes('cancel')) {
    return 'cancel_inquiry';
  }
  if (lowerMessage.includes('iade') || lowerMessage.includes('refund')) {
    return 'refund_status';
  }
  if (lowerMessage.includes('evet') || lowerMessage.includes('tamam') || lowerMessage.includes('olur') || lowerMessage.includes('yes')) {
    return 'booking_confirmed';
  }

  return 'fallback';
}

// Get AI response based on intent
export function getAIResponse(message: string): { response: string; intent: string; agentType: string } {
  const intent = detectIntent(message);
  const responses = aiResponses[intent] || aiResponses.fallback;
  const response = responses[Math.floor(Math.random() * responses.length)];

  // Determine agent type based on intent
  let agentType = 'sharpener';
  if (intent.includes('flight') || intent.includes('hotel') || intent.includes('booking')) {
    agentType = 'booking_agent';
  } else if (intent.includes('cancel') || intent.includes('refund')) {
    agentType = 'support_agent';
  }

  return { response, intent, agentType };
}

// Mock sample conversations for sidebar
export const mockConversations: Conversation[] = [
  {
    id: 'conv-1',
    title: 'Paris Seyahati',
    preview: 'Paris harika bir seçim! 🇫🇷',
    messages: [
      {
        id: 'msg-1',
        role: 'user',
        content: "Paris'e seyahat etmek istiyorum",
        timestamp: new Date(Date.now() - 3600000),
      },
      {
        id: 'msg-2',
        role: 'assistant',
        content: "Paris harika bir seçim! 🇫🇷\n\nSize en iyi seçenekleri sunabilmem için birkaç bilgiye ihtiyacım var:\n\n- **Ne zaman** gitmek istiyorsunuz?\n- **Kaç gün** kalmayı planlıyorsunuz?\n- **Kaç kişi** seyahat edecek?",
        timestamp: new Date(Date.now() - 3590000),
        agentType: 'sharpener',
        processingTimeMs: 1250,
      },
    ],
    createdAt: new Date(Date.now() - 3600000),
    updatedAt: new Date(Date.now() - 3590000),
    isActive: true,
  },
  {
    id: 'conv-2',
    title: 'Uçuş İptali',
    preview: 'İptal işlemi hakkında bilgi...',
    messages: [
      {
        id: 'msg-3',
        role: 'user',
        content: 'Uçuşumu iptal etmek istiyorum',
        timestamp: new Date(Date.now() - 86400000),
      },
      {
        id: 'msg-4',
        role: 'assistant',
        content: "İptal işlemi hakkında yardımcı olabilirim. 📋\n\n**İptal Politikamız:**\n- Kalkıştan 24+ saat önce: **Tam iade**\n- Kalkıştan 12-24 saat önce: **%50 iade**\n\nHangi rezervasyonu iptal etmek istiyorsunuz?",
        timestamp: new Date(Date.now() - 86390000),
        agentType: 'support_agent',
        processingTimeMs: 980,
      },
    ],
    createdAt: new Date(Date.now() - 86400000),
    updatedAt: new Date(Date.now() - 86390000),
    isActive: false,
  },
  {
    id: 'conv-3',
    title: 'Roma Otelleri',
    preview: 'Roma için otel önerileri...',
    messages: [
      {
        id: 'msg-5',
        role: 'user',
        content: "Roma'da kalabileceğim oteller neler?",
        timestamp: new Date(Date.now() - 172800000),
      },
    ],
    createdAt: new Date(Date.now() - 172800000),
    updatedAt: new Date(Date.now() - 172800000),
    isActive: false,
  },
];
