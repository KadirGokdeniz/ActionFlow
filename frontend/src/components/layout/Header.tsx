import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Menu, Moon, Sun, Globe, Settings, Wifi, WifiOff, Plane } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUI } from '@/contexts/UIContext';
import { checkHealth } from '@/services/api';
import { cn } from '@/lib/utils';

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { theme, toggleTheme, language, toggleLanguage, t, isMobile } = useUI();
  const [isConnected, setIsConnected] = useState<boolean | null>(null);

  // Check API health on mount
  useEffect(() => {
    const check = async () => {
      try {
        const health = await checkHealth();
        setIsConnected(health.status === 'healthy');
      } catch {
        setIsConnected(false);
      }
    };

    check();
    const interval = setInterval(check, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 border-b border-border/50 bg-background/80 backdrop-blur-sm flex items-center justify-between px-4 sticky top-0 z-50">
      {/* Left: Menu + Logo */}
      <div className="flex items-center gap-3">
        {isMobile && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuClick}
            className="rounded-xl"
          >
            <Menu className="h-5 w-5" />
          </Button>
        )}

        <div className="flex items-center gap-2">
          <motion.div
            className="w-9 h-9 rounded-xl gradient-primary flex items-center justify-center shadow-lg shadow-primary/25"
            whileHover={{ scale: 1.05 }}
          >
            <Plane className="h-5 w-5 text-white" />
          </motion.div>
          <div className="flex flex-col">
            <span className="font-semibold text-lg leading-tight">ActionFlow</span>
            <span className="text-xs text-muted-foreground leading-tight hidden sm:block">
              {t('Seyahat Asistanı', 'Travel Assistant')}
            </span>
          </div>
        </div>
      </div>

      {/* Center: Connection Status (desktop only) */}
      {!isMobile && (
        <div className="flex items-center gap-2 text-sm">
          {isConnected === null ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <div className="w-2 h-2 rounded-full bg-muted-foreground animate-pulse" />
              <span>{t('Bağlanıyor...', 'Connecting...')}</span>
            </div>
          ) : isConnected ? (
            <div className="flex items-center gap-2 text-success">
              <Wifi className="w-4 h-4" />
              <span>{t('Bağlı', 'Connected')}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-warning">
              <WifiOff className="w-4 h-4" />
              <span>{t('Çevrimdışı', 'Offline')}</span>
            </div>
          )}
        </div>
      )}

      {/* Right: Actions */}
      <div className="flex items-center gap-1">
        {/* Language Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleLanguage}
          className="rounded-xl relative"
          title={t('Dil değiştir', 'Change language')}
        >
          <Globe className="h-5 w-5" />
          <span className="absolute -bottom-0.5 -right-0.5 text-[10px] font-bold bg-primary text-primary-foreground rounded px-1">
            {language.toUpperCase()}
          </span>
        </Button>

        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="rounded-xl"
          title={t('Tema değiştir', 'Toggle theme')}
        >
          <motion.div
            key={theme}
            initial={{ rotate: -90, opacity: 0 }}
            animate={{ rotate: 0, opacity: 1 }}
            transition={{ duration: 0.2 }}
          >
            {theme === 'dark' ? (
              <Moon className="h-5 w-5" />
            ) : (
              <Sun className="h-5 w-5" />
            )}
          </motion.div>
        </Button>

        {/* Settings */}
        <Button
          variant="ghost"
          size="icon"
          className="rounded-xl"
          title={t('Ayarlar', 'Settings')}
        >
          <Settings className="h-5 w-5" />
        </Button>
      </div>
    </header>
  );
}
