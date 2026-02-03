import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, PhoneOff, Volume2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUI } from '@/contexts/UIContext';
import { useConversation } from '@/contexts/ConversationContext';
import { cn } from '@/lib/utils';

export function VoiceCallView() {
    const { t, toggleInteractionMode } = useUI();
    const { sendMessage, isTyping, getActiveConversation } = useConversation();

    const [isRecording, setIsRecording] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [isSynthesizing, setIsSynthesizing] = useState(false);
    const [statusText, setStatusText] = useState('');

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const silenceTimerRef = useRef<any>(null);
    const lastProcessedMessageId = useRef<string | null>(null);

    // Refs to track state and avoid stale closures in callbacks
    const isRecordingRef = useRef(false);
    const isTranscribingRef = useRef(false);
    const isSynthesizingRef = useRef(false);

    const activeConversation = getActiveConversation();
    const messages = activeConversation?.messages || [];
    const latestMessage = messages.length > 0 ? messages[messages.length - 1] : null;

    // 1. Initial State: Start listening automatically
    useEffect(() => {
        setStatusText(t('Bağlanıyor...', 'Connecting...'));
        const timer = setTimeout(() => {
            startListening();
        }, 1000);
        return () => {
            clearTimeout(timer);
            stopListening();
        };
    }, []);

    // 2. Monitor AI Response for TTS
    useEffect(() => {
        if (latestMessage &&
            latestMessage.role === 'assistant' &&
            latestMessage.id !== lastProcessedMessageId.current) {
            lastProcessedMessageId.current = latestMessage.id;
            playAssistantResponse(latestMessage.content);
        }
    }, [latestMessage]);

    const startListening = async () => {
        if (isRecordingRef.current || isTranscribingRef.current || isSynthesizingRef.current) return;

        try {
            setStatusText(t('Dinleniyor...', 'Listening...'));
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

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
                if (event.data.size > 0) audioChunksRef.current.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
                stream.getTracks().forEach(track => track.stop());
                audioContext.close();
                handleTranscription(audioBlob);
            };

            mediaRecorder.start();
            setIsRecording(true);
            isRecordingRef.current = true;
            monitorSilence();
        } catch (error) {
            console.error('Mic error:', error);
            setStatusText(t('Mikrofon hatası', 'Mic error'));
        }
    };

    const monitorSilence = () => {
        if (!analyserRef.current) return;
        const bufferLength = analyserRef.current.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const checkVolume = () => {
            if (!analyserRef.current) return;
            analyserRef.current.getByteFrequencyData(dataArray);
            const average = dataArray.reduce((p, c) => p + c, 0) / bufferLength;

            if (average < 10) {
                if (!silenceTimerRef.current) {
                    silenceTimerRef.current = setTimeout(() => {
                        if (mediaRecorderRef.current?.state === 'recording') {
                            mediaRecorderRef.current.stop();
                            setIsRecording(false);
                            isRecordingRef.current = false;
                        }
                    }, 2000);
                }
            } else {
                if (silenceTimerRef.current) {
                    clearTimeout(silenceTimerRef.current);
                    silenceTimerRef.current = null;
                }
            }
            if (mediaRecorderRef.current?.state === 'recording') requestAnimationFrame(checkVolume);
        };
        requestAnimationFrame(checkVolume);
    };

    const handleTranscription = async (blob: Blob) => {
        setIsTranscribing(true);
        isTranscribingRef.current = true;
        setStatusText(t('Düşünülüyor...', 'Thinking...'));
        try {
            const formData = new FormData();
            formData.append('file', blob, 'call.wav');
            const response = await fetch('/api/v1/voice/stt', { method: 'POST', body: formData });
            const data = await response.json();
            if (data.text) {
                await sendMessage(data.text);
            } else {
                // No speech detected, resume listening
                setIsTranscribing(false);
                isTranscribingRef.current = false;
                startListening();
            }
        } catch (error) {
            console.error('STT error:', error);
            setIsTranscribing(false);
            isTranscribingRef.current = false;
            startListening();
        }
    };

    const playAssistantResponse = async (text: string) => {
        setIsSynthesizing(true);
        isSynthesizingRef.current = true;
        setStatusText(t('Asistan konuşuyor...', 'Assistant speaking...'));
        try {
            const response = await fetch('/api/v1/voice/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const blob = await response.blob();
            const audio = new Audio(URL.createObjectURL(blob));
            audio.onended = () => {
                setIsSynthesizing(false);
                isSynthesizingRef.current = false;
                setIsTranscribing(false); // Ensure typing indicator reset
                isTranscribingRef.current = false;
                startListening(); // Back to listening loop
            };
            audio.play();
        } catch (error) {
            console.error('TTS error:', error);
            setIsSynthesizing(false);
            isSynthesizingRef.current = false;
            startListening();
        }
    };

    const stopListening = () => {
        if (mediaRecorderRef.current?.state === 'recording') {
            mediaRecorderRef.current.stop();
        }
        setIsRecording(false);
        isRecordingRef.current = false;
    };

    return (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/95 backdrop-blur-xl">
            {/* Wave Animation */}
            <div className="relative flex items-center justify-center w-64 h-64 mb-12">
                <AnimatePresence>
                    {isRecording && (
                        <motion.div
                            initial={{ scale: 0.8, opacity: 0 }}
                            animate={{ scale: 1.5, opacity: 0.1 }}
                            exit={{ opacity: 0 }}
                            transition={{ repeat: Infinity, duration: 2, ease: "easeOut" }}
                            className="absolute inset-0 bg-primary rounded-full"
                        />
                    )}
                </AnimatePresence>

                <div className={cn(
                    "relative z-10 flex items-center justify-center w-32 h-32 rounded-full transition-all duration-500 shadow-2xl",
                    isRecording ? "bg-primary glow-primary" : "bg-muted"
                )}>
                    {isTranscribing || isTyping ? (
                        <Loader2 className="w-12 h-12 text-white animate-spin" />
                    ) : isSynthesizing ? (
                        <Volume2 className="w-12 h-12 text-white animate-pulse" />
                    ) : (
                        <Mic className={cn("w-12 h-12", isRecording ? "text-white" : "text-muted-foreground")} />
                    )}
                </div>
            </div>

            {/* Transcription Preview (Latest AI Response) */}
            <div className="max-w-md px-6 text-center mb-12">
                <h3 className="text-xl font-medium mb-2">{statusText}</h3>
                <p className="text-muted-foreground animate-fade-in line-clamp-3 italic">
                    {latestMessage?.role === 'assistant' ? latestMessage.content : '...'}
                </p>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-6">
                <Button
                    size="lg"
                    variant="destructive"
                    className="h-16 w-16 rounded-full shadow-lg"
                    onClick={toggleInteractionMode}
                >
                    <PhoneOff className="h-6 w-6" />
                </Button>

                <Button
                    size="lg"
                    variant="outline"
                    className="h-16 w-16 rounded-full"
                    onClick={isRecording ? stopListening : startListening}
                    disabled={isTranscribing || isSynthesizing || isTyping}
                >
                    {isRecording ? <MicOff className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
                </Button>
            </div>
        </div>
    );
}
