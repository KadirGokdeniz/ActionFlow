import React, { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, Sparkles } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { MessageInput } from './MessageInput';
import { QuickActions } from './QuickActions';
import { TypingIndicator } from './TypingIndicator';
import { VoiceCallView } from '../voice/VoiceCallView';
import { useConversation } from '@/contexts/ConversationContext';
import { useUI } from '@/contexts/UIContext';
import { Phone, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export function ChatContainer() {
  const { getActiveConversation, sendMessage, isTyping } = useConversation();
  const { t, interactionMode, toggleInteractionMode } = useUI();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeConversation = getActiveConversation();
  const messages = activeConversation?.messages || [];

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSendMessage = async (content: string) => {
    await sendMessage(content);
  };

  const handleQuickAction = (message: string) => {
    handleSendMessage(message);
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Interaction Mode Overlay */}
      <AnimatePresence>
        {interactionMode === 'CALL' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="absolute inset-0 z-50"
          >
            <VoiceCallView />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header with Call Toggle */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border/50 bg-background/50 backdrop-blur-md">
        <div className="flex items-center gap-3">
          {interactionMode === 'CALL' && (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleInteractionMode}
              className="mr-2"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
          )}
          <h1 className="text-lg font-semibold tracking-tight">
            {activeConversation?.title || t('Yeni Sohbet', 'New Chat')}
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant={interactionMode === 'CALL' ? "default" : "outline"}
            size="sm"
            onClick={toggleInteractionMode}
            className={cn(
              "gap-2 rounded-full px-4 transition-all duration-300",
              interactionMode === 'CALL' ? "bg-primary glow-primary" : "hover:bg-primary/10"
            )}
          >
            <Phone className={cn("h-4 w-4", interactionMode === 'CALL' && "animate-pulse")} />
            {interactionMode === 'CALL' ? t('Görüşmede', 'On Call') : t('Sesli Ara', 'Voice Call')}
          </Button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-4 py-6">
        {messages.length === 0 ? (
          // Empty State
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center h-full text-center px-4"
          >
            <div className="w-20 h-20 rounded-full gradient-primary flex items-center justify-center mb-6 glow-primary">
              <Bot className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-2xl font-semibold mb-2">
              {t('Merhaba! 👋', 'Hello! 👋')}
            </h2>
            <p className="text-muted-foreground max-w-md mb-8">
              {t(
                'Ben ActionFlow, seyahat asistanınız. Uçuş, otel, rezervasyon ve daha fazlası için size yardımcı olabilirim.',
                "I'm ActionFlow, your travel assistant. I can help you with flights, hotels, bookings, and more."
              )}
            </p>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Sparkles className="w-4 h-4 text-primary" />
              <span>{t('Türkçe ve İngilizce desteklenmektedir', 'Turkish and English are supported')}</span>
            </div>
          </motion.div>
        ) : (
          // Messages List
          <div className="space-y-6 max-w-3xl mx-auto">
            <AnimatePresence initial={false}>
              {messages.map((message, index) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  isLast={index === messages.length - 1}
                />
              ))}
            </AnimatePresence>

            {/* Typing Indicator */}
            <AnimatePresence>
              {isTyping && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                >
                  <TypingIndicator />
                </motion.div>
              )}
            </AnimatePresence>

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-border/50 bg-background/80 backdrop-blur-sm p-4">
        <div className="max-w-3xl mx-auto space-y-3">
          {/* Quick Actions */}
          <QuickActions onAction={handleQuickAction} disabled={isTyping} />

          {/* Message Input */}
          <MessageInput onSend={handleSendMessage} isLoading={isTyping} />
        </div>
      </div>
    </div>
  );
}
