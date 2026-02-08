import React, { createContext, useContext, useState, useEffect } from 'react';
import { translations, defaultLanguage, getTranslation } from '../i18n/translations';

const LanguageContext = createContext();

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within LanguageProvider');
  }
  return context;
};

export const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState(() => {
    // Get from localStorage or use default
    return localStorage.getItem('callpilot_language') || defaultLanguage;
  });

  useEffect(() => {
    // Save to localStorage when language changes
    localStorage.setItem('callpilot_language', language);
    // Update HTML lang attribute
    document.documentElement.lang = language;
  }, [language]);

  const t = (path) => {
    return getTranslation(language, path);
  };

  const changeLanguage = (lang) => {
    setLanguage(lang);
  };

  const value = {
    language,
    setLanguage: changeLanguage,
    t,
    translations: translations[language] || translations[defaultLanguage]
  };

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
};
