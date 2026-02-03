import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, Bot, User, Volume2, StopCircle, Loader2 } from 'lucide-react';
import type { Message } from '@/types';
import { cn } from '@/lib/utils';
import { useUI } from '@/contexts/UIContext';

interface ChatMessageProps {
  message: Message;
  isLast?: boolean;
}

export function ChatMessage({ message, isLast = false }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const { t } = useUI();

  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSpeak = async () => {
    if (isPlaying) {
      audioRef.current?.pause();
      setIsPlaying(false);
      return;
    }

    setIsLoadingAudio(true);
    try {
      const response = await fetch('/api/v1/voice/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: message.content }),
      });

      if (!response.ok) throw new Error('TTS failed');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onplay = () => {
        setIsPlaying(true);
        setIsLoadingAudio(false);
      };

      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
      };

      audio.onerror = () => {
        setIsPlaying(false);
        setIsLoadingAudio(false);
        URL.revokeObjectURL(url);
      };

      audio.play();
    } catch (error) {
      console.error('TTS Error:', error);
      setIsLoadingAudio(false);
      alert(t('Ses çalınamadı.', 'Could not play audio.'));
    }
  };

  if (isSystem) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-center my-4"
      >
        <div className="px-4 py-2 rounded-full bg-destructive/10 text-destructive text-sm">
          {message.content}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 20 : -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={cn(
        'flex gap-3 group',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'gradient-primary text-white'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : (
          <Bot className="w-4 h-4" />
        )}
      </div>

      {/* Message Content */}
      <div
        className={cn(
          'relative max-w-[80%] md:max-w-[70%] rounded-2xl px-4 py-3',
          isUser
            ? 'bg-primary text-primary-foreground rounded-tr-sm'
            : 'chat-ai-gradient text-white rounded-tl-sm'
        )}
      >
        {/* Markdown Content */}
        <div className="prose prose-sm prose-invert max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
              ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
              li: ({ children }) => <li className="text-sm">{children}</li>,
              code: ({ children }) => (
                <code className="px-1.5 py-0.5 rounded bg-black/20 font-mono text-xs">
                  {children}
                </code>
              ),
              pre: ({ children }) => (
                <pre className="p-3 rounded-lg bg-black/20 overflow-x-auto my-2">
                  {children}
                </pre>
              ),
              hr: () => <hr className="my-3 border-white/20" />,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Action Buttons - Only for AI messages */}
        {!isUser && (
          <div className="absolute -bottom-8 left-0 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {/* Copy Button */}
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-md hover:bg-muted text-muted-foreground"
              title={t("Kopyala", "Copy")}
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-success" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>

            {/* Speak Button */}
            <button
              onClick={handleSpeak}
              disabled={isLoadingAudio}
              className={cn(
                "p-1.5 rounded-md hover:bg-muted transition-colors",
                isPlaying ? "text-primary" : "text-muted-foreground"
              )}
              title={isPlaying ? t("Durdur", "Stop") : t("Seslendir", "Speak")}
            >
              {isLoadingAudio ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : isPlaying ? (
                <StopCircle className="w-3.5 h-3.5" />
              ) : (
                <Volume2 className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        )}

        {/* Processing Time Badge */}
        {!isUser && message.processingTimeMs && (
          <div className="absolute -bottom-8 right-0 opacity-0 group-hover:opacity-100 transition-opacity text-xs text-muted-foreground">
            {t("İşlem:", "Process:")} {(message.processingTimeMs / 1000).toFixed(1)}s
          </div>
        )}
      </div>
    </motion.div>
  );
}
