import React, { createContext, useContext, useEffect, useState } from 'react';
import { darkEnterpriseThemeTokens, ThemeTokens } from './tokens';
import { APP_CONSTANTS } from '../config/constants';

type ThemeMode = 'dark' | 'light';

interface ThemeContextType {
  mode: ThemeMode;
  tokens: ThemeTokens;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<ThemeMode>(() => {
    return (localStorage.getItem(APP_CONSTANTS.STORAGE_KEYS.THEME) as ThemeMode) || 'dark';
  });

  useEffect(() => {
    localStorage.setItem(APP_CONSTANTS.STORAGE_KEYS.THEME, mode);
    document.documentElement.setAttribute('data-theme', mode);
  }, [mode]);

  const toggleTheme = () => {
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <ThemeContext.Provider value={{ mode, tokens: darkEnterpriseThemeTokens, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
