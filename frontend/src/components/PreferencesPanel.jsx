import React, { useState, useEffect } from 'react';
import './PreferencesPanel.css';

const PreferencesPanel = ({ value, onChange }) => {
  const [timeWeight, setTimeWeight] = useState(value?.time_weight || 0.5);
  const [ratingWeight, setRatingWeight] = useState(value?.rating_weight || 0.3);
  const [distanceWeight, setDistanceWeight] = useState(value?.distance_weight || 0.2);

  useEffect(() => {
    // Normalize weights to sum to 1.0
    const total = timeWeight + ratingWeight + distanceWeight;
    if (total > 0) {
      const normalized = {
        time_weight: timeWeight / total,
        rating_weight: ratingWeight / total,
        distance_weight: distanceWeight / total,
      };
      onChange(normalized);
    }
  }, [timeWeight, ratingWeight, distanceWeight, onChange]);

  const getWeightLabel = (weight) => {
    if (weight >= 0.5) return 'High Priority';
    if (weight >= 0.3) return 'Medium Priority';
    return 'Low Priority';
  };

  const getWeightColor = (weight) => {
    if (weight >= 0.5) return '#4caf50';
    if (weight >= 0.3) return '#ff9800';
    return '#9e9e9e';
  };

  return (
    <div className="preferences-panel">
      <label className="input-label">Scoring Preferences</label>
      <p className="preferences-description">
        Adjust the importance of each factor in ranking appointments
      </p>

      <div className="preference-sliders">
        <div className="preference-item">
          <div className="preference-header">
            <span className="preference-name">Time Availability</span>
            <span
              className="preference-priority"
              style={{ color: getWeightColor(timeWeight) }}
            >
              {getWeightLabel(timeWeight)}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={timeWeight}
            onChange={(e) => setTimeWeight(parseFloat(e.target.value))}
            className="preference-slider"
          />
          <div className="preference-value">
            {(timeWeight * 100).toFixed(0)}%
          </div>
        </div>

        <div className="preference-item">
          <div className="preference-header">
            <span className="preference-name">Provider Rating</span>
            <span
              className="preference-priority"
              style={{ color: getWeightColor(ratingWeight) }}
            >
              {getWeightLabel(ratingWeight)}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={ratingWeight}
            onChange={(e) => setRatingWeight(parseFloat(e.target.value))}
            className="preference-slider"
          />
          <div className="preference-value">
            {(ratingWeight * 100).toFixed(0)}%
          </div>
        </div>

        <div className="preference-item">
          <div className="preference-header">
            <span className="preference-name">Distance</span>
            <span
              className="preference-priority"
              style={{ color: getWeightColor(distanceWeight) }}
            >
              {getWeightLabel(distanceWeight)}
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={distanceWeight}
            onChange={(e) => setDistanceWeight(parseFloat(e.target.value))}
            className="preference-slider"
          />
          <div className="preference-value">
            {(distanceWeight * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      <div className="preferences-summary">
        <div className="summary-item">
          <span>Total:</span>
          <strong>
            {((timeWeight + ratingWeight + distanceWeight) * 100).toFixed(0)}%
          </strong>
        </div>
        <div className="summary-note">
          Weights are automatically normalized to sum to 100%
        </div>
      </div>
    </div>
  );
};

export default PreferencesPanel;
