import React from 'react';
import { format } from 'date-fns';
import './ResultsPanel.css';

const ResultsPanel = ({ ranked, best, onSelect }) => {
  const formatSlot = (slot) => {
    if (!slot) return null;
    try {
      const date = new Date(slot);
      return format(date, 'EEEE, MMMM d, yyyy \'at\' h:mm a');
    } catch (e) {
      return slot;
    }
  };

  if (!ranked || ranked.length === 0) {
    return (
      <div className="results-panel empty">
        <h3>No Appointments Found</h3>
        <p>Unfortunately, no providers had available slots matching your criteria.</p>
      </div>
    );
  }

  return (
    <div className="results-panel">
      <div className="results-header">
        <h2>Ranked Results</h2>
        <p className="results-subtitle">
          Found {ranked.length} available appointment{ranked.length !== 1 ? 's' : ''}
        </p>
      </div>

      <div className="results-list">
        {ranked.map((result, index) => {
          const isBest = best && result.provider?.name === best.provider?.name;
          const provider = result.provider || {};
          
          return (
            <div
              key={`${provider.name}-${index}`}
              className={`result-card ${isBest ? 'best-match' : ''}`}
              onClick={() => onSelect && onSelect(result)}
            >
              {isBest && (
                <div className="best-badge">
                  ⭐ Best Match
                </div>
              )}
              
              <div className="result-rank">
                #{index + 1}
              </div>

              <div className="result-content">
                <div className="result-header">
                  <h3 className="result-provider-name">{provider.name}</h3>
                  <div className="result-score">
                    Score: <strong>{result.score?.toFixed(2)}</strong>
                  </div>
                </div>

                <div className="result-details">
                  <div className="detail-row">
                    <span className="detail-label">Appointment:</span>
                    <span className="detail-value">
                      {formatSlot(result.slot)}
                    </span>
                  </div>
                  
                  {provider.rating && (
                    <div className="detail-row">
                      <span className="detail-label">Rating:</span>
                      <span className="detail-value">
                        ⭐ {provider.rating.toFixed(1)}/5.0
                      </span>
                    </div>
                  )}
                  
                  {provider.distance_miles && (
                    <div className="detail-row">
                      <span className="detail-label">Distance:</span>
                      <span className="detail-value">
                        {provider.distance_miles.toFixed(1)} miles
                      </span>
                    </div>
                  )}
                </div>

                {result.components && (
                  <div className="score-breakdown">
                    <div className="breakdown-title">Score Breakdown:</div>
                    <div className="breakdown-items">
                      <span className="breakdown-item">
                        Time: {result.components.time?.toFixed(2)}
                      </span>
                      <span className="breakdown-item">
                        Rating: {result.components.rating?.toFixed(2)}
                      </span>
                      <span className="breakdown-item">
                        Distance: {result.components.distance?.toFixed(2)}
                      </span>
                    </div>
                  </div>
                )}

                {onSelect && (
                  <button className="select-button">
                    Select This Appointment
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ResultsPanel;
