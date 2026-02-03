import axios, { AxiosError } from 'axios';
import type {
  SendMessageRequest,
  SendMessageResponse,
  ConversationHistory,
  HealthCheckResponse,
} from '@/types';
import { getAIResponse } from './mockData';

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'; // Default to mock mode

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response delay for mock mode (realistic feel)
const MOCK_DELAY_MIN = 800;
const MOCK_DELAY_MAX = 1500;

function getRandomDelay(): number {
  return Math.floor(Math.random() * (MOCK_DELAY_MAX - MOCK_DELAY_MIN + 1)) + MOCK_DELAY_MIN;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Error handling
function handleApiError(error: unknown): never {
  if (error instanceof AxiosError) {
    if (error.response) {
      throw new Error(`API Error: ${error.response.status} - ${error.response.data?.message || 'Unknown error'}`);
    } else if (error.request) {
      throw new Error('Bağlantı hatası. Lütfen internet bağlantınızı kontrol edin.');
    }
  }
  throw new Error('Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.');
}

// ===== API Functions =====

export async function sendMessage(request: SendMessageRequest): Promise<SendMessageResponse> {
  if (USE_MOCK) {
    // Mock mode
    const processingTime = getRandomDelay();
    await delay(processingTime);

    const { response, intent, agentType } = getAIResponse(request.message);

    return {
      conversation_id: request.conversation_id || `conv-${Date.now()}`,
      message: response,
      intent,
      agent_used: agentType,
      processing_time_ms: processingTime,
    };
  }

  try {
    const response = await apiClient.post<SendMessageResponse>('/chat/', request);
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
}

export async function getConversationHistory(conversationId: string): Promise<ConversationHistory> {
  if (USE_MOCK) {
    await delay(500);
    // Return empty history for mock mode
    return {
      conversation_id: conversationId,
      messages: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  try {
    const response = await apiClient.get<ConversationHistory>(`/chat/history/${conversationId}`);
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
}

export async function checkHealth(): Promise<HealthCheckResponse> {
  if (USE_MOCK) {
    await delay(200);
    return {
      status: 'healthy',
      mcp: {
        status: 'connected',
        tools_available: 6,
      },
    };
  }

  try {
    const response = await apiClient.get<HealthCheckResponse>('/chat/health');
    return response.data;
  } catch (error) {
    // Return unhealthy status on error
    return {
      status: 'unhealthy',
    };
  }
}

// Export config for debugging
export const apiConfig = {
  baseUrl: API_BASE_URL,
  useMock: USE_MOCK,
};
