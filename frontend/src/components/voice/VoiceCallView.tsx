import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, PhoneOff, Volume2, Loader2, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUI } from '@/contexts/UIContext';
import { cn } from '@/lib/utils';

const WS_BASE = import.meta.env.VITE_WS_URL?.replace('/chat/ws', '') || 'ws://localhost:8000/api/v1';
const SAMPLE_RATE = 24000;
const BUFFER_SIZE = 4096;

export function VoiceCallView() {
  const { t, toggleInteractionMode } = useUI();
  const [status, setStatus] = useState<'connecting' | 'ready' | 'listening' | 'thinking' | 'speaking' | 'error'>('connecting');
  const [userTranscript, setUserTranscript] = useState('');
  const [aiTranscript, setAiTranscript] = useState('');
  const [toolCall, setToolCall] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioQueueRef = useRef<Float32Array[]>([]);
  const isPlayingRef = useRef(false);

  // PCM16 -> Float32
  const pcm16ToFloat32 = (buffer: ArrayBuffer): Float32Array => {
    const int16 = new Int16Array(buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768.0;
    }
    return float32;
  };

  // Float32 -> PCM16 base64
  const float32ToPcm16Base64 = (float32: Float32Array): string => {
    const int16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    const bytes = new Uint8Array(int16.buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  // Play audio queue
  const playNextChunk = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
    isPlayingRef.current = true;

    const ctx = audioCtxRef.current!;
    const chunk = audioQueueRef.current.shift()!;
    const buffer = ctx.createBuffer(1, chunk.length, SAMPLE_RATE);
    buffer.copyToChannel(chunk, 0);

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.onended = () => {
      isPlayingRef.current = false;
      if (audioQueueRef.current.length > 0) playNextChunk();
      else setStatus('listening');
    };
    source.start();
    setStatus('speaking');
  }, []);

  // Connect WebSocket
  useEffect(() => {
    const customerId = `user_${Date.now()}`;
    const ws = new WebSocket(`${WS_BASE}/voice/realtime?customer_id=${customerId}`);
    wsRef.current = ws;

    ws.onmessage = async (event) => {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'ready':
          setStatus('ready');
          startMicrophone();
          break;

        case 'speech_started':
          setStatus('listening');
          setAiTranscript('');
          setToolCall(null);
          // Stop current playback
          audioQueueRef.current = [];
          isPlayingRef.current = false;
          break;

        case 'speech_stopped':
          setStatus('thinking');
          break;

        case 'user_transcript':
          setUserTranscript(data.text);
          break;

        case 'audio': {
          if (!audioCtxRef.current) break;
          const raw = atob(data.audio);
          const bytes = new Uint8Array(raw.length);
          for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
          const float32 = pcm16ToFloat32(bytes.buffer);
          audioQueueRef.current.push(float32);
          playNextChunk();
          break;
        }

        case 'ai_transcript':
          setAiTranscript(prev => prev + data.text);
          break;

        case 'tool_call':
          setToolCall(data.name);
          break;

        case 'error':
          setStatus('error');
          console.error('Realtime error:', data.message);
          break;
      }
    };

    ws.onerror = () => setStatus('error');
    ws.onclose = () => console.log('WebSocket closed');

    audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
      sampleRate: SAMPLE_RATE
    });

    return () => {
      ws.close();
      stopMicrophone();
      audioCtxRef.current?.close();
    };
  }, []);

  const startMicrophone = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const ctx = audioCtxRef.current!;
      const source = ctx.createMediaStreamSource(stream);
      const processor = ctx.createScriptProcessor(BUFFER_SIZE, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) return;
        const float32 = e.inputBuffer.getChannelData(0);
        // Resample to 24kHz if needed
        const base64 = float32ToPcm16Base64(float32);
        wsRef.current.send(JSON.stringify({ type: 'audio', audio: base64 }));
      };

      source.connect(processor);
      processor.connect(ctx.destination);
    } catch (err) {
      console.error('Mic error:', err);
      setStatus('error');
    }
  };

  const stopMicrophone = () => {
    processorRef.current?.disconnect();
    streamRef.current?.getTracks().forEach(t => t.stop());
  };

  const statusLabel: Record<typeof status, string> = {
    connecting: t('Baglaniyor...', 'Connecting...'),
    ready: t('Hazir', 'Ready'),
    listening: t('Dinleniyor...', 'Listening...'),
    thinking: t('Dusunuyor...', 'Thinking...'),
    speaking: t('Konusuyor...', 'Speaking...'),
    error: t('Hata olustu', 'Error occurred'),
  };

  const isListening = status === 'listening' || status === 'ready';

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/95 backdrop-blur-xl">
      {/* Latency badge */}
      <div className="absolute top-6 right-6 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-success/10 text-success text-xs font-medium">
        <Zap className="w-3 h-3" />
        Realtime API ~500ms
      </div>

      {/* Wave animation */}
      <div className="relative flex items-center justify-center w-48 h-48 mb-8">
        <AnimatePresence>
          {isListening && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1.6, opacity: 0.1 }}
              exit={{ opacity: 0 }}
              transition={{ repeat: Infinity, duration: 1.8, ease: 'easeOut' }}
              className="absolute inset-0 bg-primary rounded-full"
            />
          )}
        </AnimatePresence>

        <div className={cn(
          "relative z-10 w-28 h-28 rounded-full flex items-center justify-center shadow-2xl transition-all duration-500",
          isListening ? "bg-primary glow-primary" :
          status === 'speaking' ? "bg-accent glow-accent" :
          status === 'thinking' ? "bg-warning/80" : "bg-muted"
        )}>
          {status === 'thinking' ? (
            <Loader2 className="w-10 h-10 text-white animate-spin" />
          ) : status === 'speaking' ? (
            <Volume2 className="w-10 h-10 text-white animate-pulse" />
          ) : (
            <Mic className={cn("w-10 h-10", isListening ? "text-white" : "text-muted-foreground")} />
          )}
        </div>
      </div>

      {/* Status */}
      <h3 className="text-xl font-medium mb-2">{statusLabel[status]}</h3>

      {/* Tool call indicator */}
      {toolCall && (
        <div className="mb-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs">
          {toolCall.replace(/_/g, ' ')}...
        </div>
      )}

      {/* Transcripts */}
      <div className="max-w-sm w-full px-6 space-y-2 mb-10 text-center min-h-[80px]">
        {userTranscript && (
          <p className="text-sm text-muted-foreground italic">"{userTranscript}"</p>
        )}
        {aiTranscript && (
          <p className="text-sm font-medium">{aiTranscript}</p>
        )}
      </div>

      {/* Controls */}
      <Button
        size="lg"
        variant="destructive"
        className="h-16 w-16 rounded-full shadow-lg"
        onClick={toggleInteractionMode}
      >
        <PhoneOff className="h-6 w-6" />
      </Button>
    </div>
  );
}
