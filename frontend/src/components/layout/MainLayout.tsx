import React from 'react';
import { Header } from './Header';
import { ConversationSidebar } from '@/components/sidebar/ConversationSidebar';
import { ChatContainer } from '@/components/chat/ChatContainer';
import { useUI } from '@/contexts/UIContext';

export function MainLayout() {
  const { sidebarOpen, toggleSidebar, isMobile } = useUI();

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      {/* Header */}
      <Header onMenuClick={toggleSidebar} />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <ConversationSidebar
          isOpen={sidebarOpen}
          onClose={() => toggleSidebar()}
        />

        {/* Chat Area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatContainer />
        </main>
      </div>
    </div>
  );
}
