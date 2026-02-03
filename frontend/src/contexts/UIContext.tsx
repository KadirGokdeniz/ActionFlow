import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import type { Theme, Language, UIState, InteractionMode } from '@/types';

interface UIContextType extends UIState {
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  toggleLanguage: () => void;
  setLanguage: (language: Language) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSettings: () => void;
  setSettingsOpen: (open: boolean) => void;
  t: (tr: string, en: string) => string;
  interactionMode: InteractionMode;
  setInteractionMode: (mode: InteractionMode) => void;
  toggleInteractionMode: () => void;
}

const UIContext = createContext<UIContextType | undefined>(undefined);

const THEME_KEY = 'actionflow-theme';
const LANGUAGE_KEY = 'actionflow-language';

interface UIProviderProps {
  children: ReactNode;
}

export function UIProvider({ children }: UIProviderProps) {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(THEME_KEY) as Theme | null;
      if (saved) return saved;
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'dark';
  });

  const [language, setLanguageState] = useState<Language>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(LANGUAGE_KEY) as Language | null;
      if (saved) return saved;
      // Detect browser language
      const browserLang = navigator.language.toLowerCase();
      return browserLang.startsWith('tr') ? 'tr' : 'en';
    }
    return 'en';
  });

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [interactionMode, setInteractionModeState] = useState<InteractionMode>('CHAT');

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  // Save language preference
  useEffect(() => {
    localStorage.setItem(LANGUAGE_KEY, language);
  }, [language]);

  // Handle responsive sidebar
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) {
        setSidebarOpen(false);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
  }, []);

  const toggleLanguage = useCallback(() => {
    setLanguageState((prev) => (prev === 'tr' ? 'en' : 'tr'));
  }, []);

  const setLanguage = useCallback((newLanguage: Language) => {
    setLanguageState(newLanguage);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  const toggleSettings = useCallback(() => {
    setSettingsOpen((prev) => !prev);
  }, []);

  const setInteractionMode = useCallback((mode: InteractionMode) => {
    setInteractionModeState(mode);
  }, []);

  const toggleInteractionMode = useCallback(() => {
    setInteractionModeState((prev) => (prev === 'CHAT' ? 'CALL' : 'CHAT'));
  }, []);

  // Translation helper
  const t = useCallback(
    (tr: string, en: string) => {
      return language === 'tr' ? tr : en;
    },
    [language]
  );

  const value: UIContextType = {
    theme,
    language,
    sidebarOpen,
    settingsOpen,
    isMobile,
    toggleTheme,
    setTheme,
    toggleLanguage,
    setLanguage,
    toggleSidebar,
    setSidebarOpen,
    toggleSettings,
    setSettingsOpen,
    t,
    interactionMode,
    setInteractionMode,
    toggleInteractionMode,
  };

  return <UIContext.Provider value={value}>{children}</UIContext.Provider>;
}

export function useUI() {
  const context = useContext(UIContext);
  if (context === undefined) {
    throw new Error('useUI must be used within a UIProvider');
  }
  return context;
}
