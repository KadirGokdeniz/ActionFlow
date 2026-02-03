import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Search, MessageSquare, Trash2, Plane, Calendar, Users, MapPin, ChevronDown } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { tr, enUS } from 'date-fns/locale';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useConversation } from '@/contexts/ConversationContext';
import { useTravelContext } from '@/contexts/TravelContext';
import { useUI } from '@/contexts/UIContext';
import { cn } from '@/lib/utils';

interface ConversationSidebarProps {
  isOpen: boolean;
  onClose?: () => void;
}

export function ConversationSidebar({ isOpen, onClose }: ConversationSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [contextExpanded, setContextExpanded] = useState(true);
  
  const { conversations, activeConversationId, setActiveConversation, createConversation, deleteConversation, searchConversations } = useConversation();
  const { travelData, hasContext } = useTravelContext();
  const { language, t, isMobile } = useUI();

  const filteredConversations = searchQuery ? searchConversations(searchQuery) : conversations;
  const locale = language === 'tr' ? tr : enUS;

  const handleNewChat = () => {
    createConversation();
    if (isMobile && onClose) {
      onClose();
    }
  };

  const handleSelectConversation = (id: string) => {
    setActiveConversation(id);
    if (isMobile && onClose) {
      onClose();
    }
  };

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 space-y-3">
        {/* New Chat Button */}
        <Button
          onClick={handleNewChat}
          className="w-full gradient-primary text-white rounded-xl h-11 font-medium shadow-lg shadow-primary/25 hover:opacity-90 transition-opacity"
        >
          <Plus className="h-5 w-5 mr-2" />
          {t('Yeni Sohbet', 'New Chat')}
        </Button>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder={t('Konuşma ara...', 'Search conversations...')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 rounded-xl bg-muted/50 border-0 focus-visible:ring-1"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-2">
        {filteredConversations.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm">
            {searchQuery
              ? t('Aramanızla eşleşen konuşma bulunamadı', 'No conversations match your search')
              : t('Henüz konuşma yok', 'No conversations yet')}
          </div>
        ) : (
          <div className="space-y-1">
            {filteredConversations.map((conversation) => (
              <motion.div
                key={conversation.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="relative group"
              >
                <button
                  onClick={() => handleSelectConversation(conversation.id)}
                  className={cn(
                    'w-full text-left p-3 rounded-xl transition-all duration-200',
                    'hover:bg-muted/50',
                    activeConversationId === conversation.id
                      ? 'bg-primary/10 border border-primary/30'
                      : 'border border-transparent'
                  )}
                >
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                      activeConversationId === conversation.id
                        ? 'gradient-primary text-white'
                        : 'bg-muted text-muted-foreground'
                    )}>
                      <MessageSquare className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-sm truncate">{conversation.title}</h3>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {conversation.preview || t('Mesaj yok', 'No messages')}
                      </p>
                      <span className="text-xs text-muted-foreground/70 mt-1 block">
                        {formatDistanceToNow(conversation.updatedAt, { addSuffix: true, locale })}
                      </span>
                    </div>
                  </div>
                </button>

                {/* Delete Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteConversation(conversation.id);
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-all"
                  title={t('Sil', 'Delete')}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Travel Context Panel */}
      <div className="border-t border-border/50 p-3">
        <button
          onClick={() => setContextExpanded(!contextExpanded)}
          className="flex items-center justify-between w-full p-2 rounded-lg hover:bg-muted/50 transition-colors"
        >
          <span className="text-sm font-medium text-muted-foreground">
            {t('Seyahat Bilgileri', 'Travel Context')}
          </span>
          <motion.div
            animate={{ rotate: contextExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          </motion.div>
        </button>

        <AnimatePresence>
          {contextExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              {hasContext ? (
                <div className="p-3 mt-2 rounded-xl bg-muted/30 space-y-2 text-sm">
                  {(travelData.origin || travelData.destination) && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <MapPin className="w-4 h-4 text-primary" />
                      <span>
                        {travelData.origin || '?'} → {travelData.destination || '?'}
                      </span>
                    </div>
                  )}
                  {(travelData.departureDate || travelData.returnDate) && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Calendar className="w-4 h-4 text-primary" />
                      <span>
                        {travelData.departureDate || '?'} - {travelData.returnDate || '?'}
                      </span>
                    </div>
                  )}
                  {travelData.travelers && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Users className="w-4 h-4 text-primary" />
                      <span>{travelData.travelers} {t('Yolcu', 'Travelers')}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-3 mt-2 rounded-xl bg-muted/30 text-sm text-muted-foreground text-center">
                  {t('Henüz seyahat bilgisi yok', 'No travel info yet')}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );

  // Mobile: Full-screen overlay
  if (isMobile) {
    return (
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40"
            />

            {/* Sidebar */}
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed left-0 top-0 bottom-0 w-80 max-w-[85vw] bg-background border-r border-border/50 z-50 shadow-2xl"
            >
              {sidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    );
  }

  // Desktop: Static sidebar
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 320, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="h-full border-r border-border/50 bg-background/50 backdrop-blur-sm overflow-hidden flex-shrink-0"
        >
          <div className="w-80 h-full">
            {sidebarContent}
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
