import React from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import './LandingPage.css';

const LandingPage = ({ onStartDemo }) => {
  const { t } = useLanguage();
  return (
    <div className="landing-page">
      <div className="landing-content">
        <div className="hero-section">
          <h1 className="hero-title">
            <span className="brand-name">{t('landing.title')}</span>
            <span className="brand-tagline">{t('landing.tagline')}</span>
          </h1>
          <p className="hero-subtitle">
            {t('landing.subtitle')}
          </p>
          <p className="hero-description">
            {t('landing.description')}
          </p>
          
          <div className="hero-features">
            <div className="feature-item">
              <div className="feature-icon">🚀</div>
              <div className="feature-text">
                <strong>{t('landing.features.parallel.title')}</strong>
                <span>{t('landing.features.parallel.desc')}</span>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon">🤖</div>
              <div className="feature-text">
                <strong>{t('landing.features.negotiation.title')}</strong>
                <span>{t('landing.features.negotiation.desc')}</span>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon">⭐</div>
              <div className="feature-text">
                <strong>{t('landing.features.matching.title')}</strong>
                <span>{t('landing.features.matching.desc')}</span>
              </div>
            </div>
          </div>

          <button className="start-demo-button" onClick={onStartDemo}>
            {t('landing.startDemo')}
          </button>
        </div>

        <div className="demo-preview">
          <div className="preview-card">
            <h3>{t('landing.howItWorks')}</h3>
            <ol className="steps-list">
              <li>{t('landing.steps.step1')}</li>
              <li>{t('landing.steps.step2')}</li>
              <li>{t('landing.steps.step3')}</li>
              <li>{t('landing.steps.step4')}</li>
              <li>{t('landing.steps.step5')}</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
