import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { Conversation, Message, ConversationState } from '@/types';
import { sendMessage as apiSendMessage, getConversationHistory } from '@/services/api';

interface ConversationContextType extends ConversationState {
  createConversation: () => Conversation;
  setActiveConversation: (id: string | null) => void;
  deleteConversation: (id: string) => void;
  sendMessage: (content: string) => Promise<void>;
  clearError: () => void;
  getActiveConversation: () => Conversation | undefined;
  searchConversations: (query: string) => Conversation[];
}

const ConversationContext = createContext<ConversationContextType | undefined>(undefined);

interface ConversationProviderProps {
  children: ReactNode;
  customerId?: string;
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export function ConversationProvider({ children, customerId = 'user_demo' }: ConversationProviderProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);

  const getActiveConversation = useCallback(() => {
    return conversations.find((c) => c.id === activeConversationId);
  }, [conversations, activeConversationId]);

  const createConversation = useCallback(() => {
    const newConversation: Conversation = {
      id: generateId(),
      title: 'Yeni Sohbet',
      preview: '',
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      isActive: true,
    };

    setConversations((prev) => [newConversation, ...prev]);
    setActiveConversationId(newConversation.id);
    return newConversation;
  }, []);

  const setActiveConversation = useCallback((id: string | null) => {
    setActiveConversationId(id);
    setError(null);
  }, []);

  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        setActiveConversationId(null);
      }
    },
    [activeConversationId]
  );

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      let conversationId = activeConversationId;
      let targetConversation = getActiveConversation();

      // Create new conversation if none exists
      if (!conversationId || !targetConversation) {
        targetConversation = createConversation();
        conversationId = targetConversation.id;
      }

      // Create user message
      const userMessage: Message = {
        id: generateId(),
        role: 'user',
        content: content.trim(),
        timestamp: new Date(),
      };

      // Update conversation with user message
      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === conversationId) {
            const isFirstMessage = c.messages.length === 0;
            return {
              ...c,
              messages: [...c.messages, userMessage],
              preview: content.trim().slice(0, 50),
              title: isFirstMessage ? content.trim().slice(0, 30) : c.title,
              updatedAt: new Date(),
            };
          }
          return c;
        })
      );

      setIsTyping(true);
      setError(null);

      try {
        const response = await apiSendMessage({
          message: content,
          customer_id: customerId,
          conversation_id: conversationId,
          language: 'en',
        });

        // Update conversation ID if backend returned a new one
        const realConversationId = response.conversation_id;

        // Create assistant message
        const assistantMessage: Message = {
          id: generateId(),
          role: 'assistant',
          content: response.message,
          timestamp: new Date(),
          agentType: response.agent_used,
          processingTimeMs: response.processing_time_ms,
        };

        // Update conversation with assistant message AND sync ID if needed
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === conversationId) {
              return {
                ...c,
                id: realConversationId, // Sync with backend ID
                messages: [...c.messages, assistantMessage],
                updatedAt: new Date(),
              };
            }
            return c;
          })
        );

        // Update active conversation ID if it changed
        if (conversationId !== realConversationId) {
          setActiveConversationId(realConversationId);
        }
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Mesaj gönderilemedi. Lütfen tekrar deneyin.';
        setError(errorMessage);

        // Add error message to conversation
        const errorSystemMessage: Message = {
          id: generateId(),
          role: 'system',
          content: errorMessage,
          timestamp: new Date(),
        };

        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === conversationId) {
              return {
                ...c,
                messages: [...c.messages, errorSystemMessage],
                updatedAt: new Date(),
              };
            }
            return c;
          })
        );
      } finally {
        setIsTyping(false);
      }
    },
    [activeConversationId, getActiveConversation, createConversation, customerId]
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const searchConversations = useCallback(
    (query: string) => {
      if (!query.trim()) return conversations;
      const lowerQuery = query.toLowerCase();
      return conversations.filter(
        (c) =>
          c.title.toLowerCase().includes(lowerQuery) ||
          c.preview.toLowerCase().includes(lowerQuery) ||
          c.messages.some((m) => m.content.toLowerCase().includes(lowerQuery))
      );
    },
    [conversations]
  );

  const value: ConversationContextType = {
    conversations,
    activeConversationId,
    isLoading,
    error,
    isTyping,
    createConversation,
    setActiveConversation,
    deleteConversation,
    sendMessage,
    clearError,
    getActiveConversation,
    searchConversations,
  };

  return <ConversationContext.Provider value={value}>{children}</ConversationContext.Provider>;
}

export function useConversation() {
  const context = useContext(ConversationContext);
  if (context === undefined) {
    throw new Error('useConversation must be used within a ConversationProvider');
  }
  return context;
}
