import React from 'react';
import { format } from 'date-fns';
import './ProviderCard.css';

const ProviderCard = ({ provider, result, status = 'waiting' }) => {
  const getStatusClass = () => {
    switch (status) {
      case 'calling':
        return 'status-calling';
      case 'success':
        return 'status-success';
      case 'failed':
      case 'error':
      case 'timeout':
        return 'status-error';
      case 'no_availability':
        return 'status-no-availability';
      default:
        return 'status-waiting';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'waiting':
        return 'Waiting...';
      case 'calling':
        return 'Calling...';
      case 'success':
      case 'ok':
        return 'Success';
      case 'failed':
      case 'error':
        return 'Failed';
      case 'timeout':
        return 'Timeout';
      case 'no_availability':
        return 'No Availability';
      default:
        return status;
    }
  };

  const formatSlot = (slot) => {
    if (!slot) return null;
    try {
      const date = new Date(slot);
      return format(date, 'MMM d, yyyy h:mm a');
    } catch (e) {
      return slot;
    }
  };

  const providerData = result?.provider || provider || {};
  const slot = result?.slot;
  const score = result?.score;
  const components = result?.components;

  return (
    <div className={`provider-card ${getStatusClass()}`}>
      <div className="provider-header">
        <h3 className="provider-name">{providerData.name || 'Unknown Provider'}</h3>
        <span className={`status-badge ${getStatusClass()}`}>
          {getStatusText()}
        </span>
      </div>

      <div className="provider-info">
        {providerData.rating && (
          <div className="info-item">
            <span className="info-label">Rating:</span>
            <span className="info-value">
              ⭐ {providerData.rating.toFixed(1)}/5.0
            </span>
          </div>
        )}
        {providerData.distance_miles && (
          <div className="info-item">
            <span className="info-label">Distance:</span>
            <span className="info-value">{providerData.distance_miles.toFixed(1)} miles</span>
          </div>
        )}
      </div>

      {slot && (
        <div className="appointment-slot">
          <div className="slot-label">Available Slot:</div>
          <div className="slot-time">{formatSlot(slot)}</div>
        </div>
      )}

      {score !== undefined && (
        <div className="score-section">
          <div className="score-total">
            Score: <strong>{score.toFixed(2)}</strong>
          </div>
          {components && (
            <div className="score-breakdown">
              <span className="breakdown-item">Time: {components.time?.toFixed(2)}</span>
              <span className="breakdown-item">Rating: {components.rating?.toFixed(2)}</span>
              <span className="breakdown-item">Distance: {components.distance?.toFixed(2)}</span>
            </div>
          )}
        </div>
      )}

      {result?.error && (
        <div className="error-message">
          {result.error}
        </div>
      )}
    </div>
  );
};

export default ProviderCard;
