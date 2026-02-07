import React from 'react';
import './LandingPage.css';

const LandingPage = ({ onStartDemo }) => {
  return (
    <div className="landing-page">
      <div className="landing-content">
        <div className="hero-section">
          <h1 className="hero-title">
            <span className="brand-name">CallPilot</span>
            <span className="brand-tagline">AI</span>
          </h1>
          <p className="hero-subtitle">
            Agentic Voice AI for Autonomous Appointment Scheduling
          </p>
          <p className="hero-description">
            Stop wasting time on hold. Let AI call multiple providers simultaneously,
            negotiate the best appointment slot, and book it for you—all in seconds.
          </p>
          
          <div className="hero-features">
            <div className="feature-item">
              <div className="feature-icon">🚀</div>
              <div className="feature-text">
                <strong>Parallel Calls</strong>
                <span>Call up to 15 providers at once</span>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon">🤖</div>
              <div className="feature-text">
                <strong>AI Negotiation</strong>
                <span>Natural conversation with receptionists</span>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon">⭐</div>
              <div className="feature-text">
                <strong>Smart Matching</strong>
                <span>Best appointment based on your preferences</span>
              </div>
            </div>
          </div>

          <button className="start-demo-button" onClick={onStartDemo}>
            Start Demo
          </button>
        </div>

        <div className="demo-preview">
          <div className="preview-card">
            <h3>How It Works</h3>
            <ol className="steps-list">
              <li>Tell us what service you need</li>
              <li>Set your preferred time window</li>
              <li>Watch AI call providers in parallel</li>
              <li>Get ranked results instantly</li>
              <li>Confirm your best match</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
