import React from 'react';
import { motion } from 'framer-motion';

interface TypingIndicatorProps {
  className?: string;
}

export function TypingIndicator({ className = '' }: TypingIndicatorProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className="flex items-center gap-1.5 px-4 py-3 rounded-2xl chat-ai-gradient">
        <motion.div
          className="w-2 h-2 bg-white/80 rounded-full"
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
        />
        <motion.div
          className="w-2 h-2 bg-white/80 rounded-full"
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: 0.15 }}
        />
        <motion.div
          className="w-2 h-2 bg-white/80 rounded-full"
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: 0.3 }}
        />
      </div>
      <span className="text-sm text-muted-foreground">ActionFlow düşünüyor...</span>
    </div>
  );
}
