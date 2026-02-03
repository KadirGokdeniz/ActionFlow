import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { motion } from 'framer-motion';
import { Send, Mic, Paperclip } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUI } from '@/contexts/UIContext';
import { cn } from '@/lib/utils';

interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  isLoading?: boolean;
}

export function MessageInput({ onSend, disabled = false, isLoading = false }: MessageInputProps) {
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Audio Context for silence detection
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const silenceTimerRef = useRef<any>(null);

  const { t } = useUI();

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const newHeight = Math.min(textarea.scrollHeight, 150); // Max 5 lines approximately
      textarea.style.height = `${newHeight}px`;
    }
  }, [message]);

  const handleSubmit = (overrideMessage?: string) => {
    const messageToSend = overrideMessage || message;
    if (messageToSend.trim() && !disabled && !isLoading && !isTranscribing) {
      onSend(messageToSend.trim());
      setMessage('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Setup Silence Detection
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      analyser.fftSize = 256;

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await handleTranscription(audioBlob, true); // Auto-send enabled
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
        if (audioContext.state !== 'closed') {
          audioContext.close();
        }
      };

      mediaRecorder.start();
      setIsRecording(true);

      // Start monitoring silence
      monitorSilence();

    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert(t('Mikrofona erişilemedi.', 'Could not access microphone.'));
    }
  };

  const monitorSilence = () => {
    if (!analyserRef.current || !isRecording) return;

    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const checkVolume = () => {
      if (!isRecording || !analyserRef.current) return;

      analyserRef.current.getByteFrequencyData(dataArray);
      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i];
      }
      const average = sum / bufferLength;

      // Silence threshold (can be adjusted)
      const THRESHOLD = 10;
      const SILENCE_DURATION = 2000; // 2 seconds

      if (average < THRESHOLD) {
        if (!silenceTimerRef.current) {
          silenceTimerRef.current = setTimeout(() => {
            stopRecording();
          }, SILENCE_DURATION);
        }
      } else {
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }
      }

      if (isRecording) {
        requestAnimationFrame(checkVolume);
      }
    };

    requestAnimationFrame(checkVolume);
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
      }
    }
  };

  const handleTranscription = async (audioBlob: Blob, autoSend: boolean = false) => {
    setIsTranscribing(true);
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.wav');

      const response = await fetch('/api/v1/voice/stt', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Transcription failed');
      }

      const data = await response.json();
      if (data.text) {
        if (autoSend) {
          handleSubmit(data.text);
        } else {
          setMessage((prev) => (prev ? `${prev} ${data.text}` : data.text));
        }
      }
    } catch (error) {
      console.error('Transcription error:', error);
      alert(t('Ses çözümlenemedi.', 'Could not transcribe audio.'));
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
    if (e.key === 'Escape') {
      setMessage('');
    }
  };

  const canSend = message.trim().length > 0 && !disabled && !isLoading && !isTranscribing;

  return (
    <div className="relative">
      <div className={cn(
        "flex items-end gap-2 p-2 rounded-2xl bg-card/50 backdrop-blur-sm border transition-all duration-300 shadow-lg",
        isRecording ? "border-primary ring-2 ring-primary/20" : "border-border/50"
      )}>
        {/* Attachment Button */}
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="flex-shrink-0 h-10 w-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/50"
          title={t('Dosya ekle', 'Attach file')}
          disabled={isRecording || isTranscribing}
        >
          <Paperclip className="h-5 w-5" />
        </Button>

        {/* Textarea */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isRecording
                ? t('Dinleniyor...', 'Listening...')
                : isTranscribing
                  ? t('Çözümleniyor...', 'Transcribing...')
                  : t('Mesajınızı yazın...', 'Type your message...')
            }
            disabled={disabled || isLoading || isRecording || isTranscribing}
            rows={1}
            className={cn(
              'w-full resize-none bg-transparent border-0 outline-none',
              'text-foreground placeholder:text-muted-foreground',
              'py-2.5 px-1 text-sm leading-relaxed',
              'focus:ring-0 focus:outline-none',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'custom-scrollbar transition-opacity duration-300',
              (isRecording || isTranscribing) && "opacity-50"
            )}
            style={{ maxHeight: '150px' }}
          />
        </div>

        {/* Voice Button */}
        <Button
          type="button"
          variant={isRecording ? "default" : "ghost"}
          size="icon"
          onClick={isRecording ? stopRecording : startRecording}
          disabled={disabled || isLoading || isTranscribing}
          className={cn(
            "flex-shrink-0 h-10 w-10 rounded-xl transition-all duration-300",
            isRecording
              ? "bg-destructive text-destructive-foreground hover:bg-destructive/90 animate-pulse"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
          title={isRecording ? t('Kaydı durdur', 'Stop recording') : t('Sesli mesaj', 'Voice message')}
        >
          {isTranscribing ? (
            <motion.div
              className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            />
          ) : (
            <Mic className={cn("h-5 w-5", isRecording && "fill-current")} />
          )}
        </Button>

        {/* Send Button */}
        <motion.div whileTap={{ scale: 0.95 }}>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={!canSend}
            className={cn(
              'flex-shrink-0 h-10 w-10 rounded-xl',
              'gradient-primary text-white',
              'hover:opacity-90 transition-opacity',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'shadow-lg shadow-primary/25'
            )}
          >
            {isLoading ? (
              <motion.div
                className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </Button>
        </motion.div>
      </div>

      {/* Character count hint */}
      {message.length > 500 && !isRecording && !isTranscribing && (
        <div className="absolute -top-6 right-2 text-xs text-muted-foreground">
          {message.length} / 2000
        </div>
      )}
    </div>
  );
}
