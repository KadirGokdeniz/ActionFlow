// ActionFlow Type Definitions

// ===== API Types =====

export interface SendMessageRequest {
  message: string;
  customer_id: string;
  conversation_id?: string;
  language?: string;
}

export interface SendMessageResponse {
  conversation_id: string;
  message: string;
  intent?: string;
  agent_used?: string;
  processing_time_ms: number;
}

export interface HistoryMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  agent_type?: string;
}

export interface ConversationHistory {
  conversation_id: string;
  messages: HistoryMessage[];
  created_at: string;
  updated_at: string;
}

export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  mcp?: {
    status: 'connected' | 'disconnected';
    tools_available: number;
  };
}

// ===== UI Types =====

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  agentType?: string;
  processingTimeMs?: number;
  isLoading?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  preview: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  isActive: boolean;
}

export interface TravelContextData {
  origin?: string;
  destination?: string;
  departureDate?: string;
  returnDate?: string;
  travelers?: number;
  budget?: number;
  tripType?: 'one-way' | 'round-trip' | 'multi-city';
}

// ===== Rich Content Types =====

export interface FlightInfo {
  id: string;
  airline: string;
  airlineLogo?: string;
  flightNumber: string;
  origin: {
    code: string;
    city: string;
    time: string;
  };
  destination: {
    code: string;
    city: string;
    time: string;
  };
  duration: string;
  stops: number;
  price: number;
  currency: string;
  class: 'economy' | 'business' | 'first';
}

export interface HotelInfo {
  id: string;
  name: string;
  image?: string;
  location: string;
  rating: number;
  reviewCount: number;
  pricePerNight: number;
  currency: string;
  amenities: string[];
}

export interface BookingInfo {
  id: string;
  referenceNumber: string;
  type: 'flight' | 'hotel' | 'package';
  status: 'confirmed' | 'pending' | 'cancelled' | 'completed';
  details: string;
  date: string;
  price: number;
  currency: string;
}

// ===== Context Types =====

export type Theme = 'light' | 'dark';
export type Language = 'tr' | 'en';
export type InteractionMode = 'CHAT' | 'CALL';

export interface UIState {
  theme: Theme;
  language: Language;
  sidebarOpen: boolean;
  settingsOpen: boolean;
  isMobile: boolean;
  interactionMode: InteractionMode;
}

export interface ConversationState {
  conversations: Conversation[];
  activeConversationId: string | null;
  isLoading: boolean;
  error: string | null;
  isTyping: boolean;
}

// ===== Utility Types =====

export type MessageRole = 'user' | 'assistant' | 'system';

export interface QuickAction {
  id: string;
  icon: string;
  labelTr: string;
  labelEn: string;
  message: string;
}
