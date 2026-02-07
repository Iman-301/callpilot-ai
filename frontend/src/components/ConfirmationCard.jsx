import React, { useState } from 'react';
import { format } from 'date-fns';
import './ConfirmationCard.css';

const ConfirmationCard = ({ appointment, onConfirm, onCancel }) => {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);

  const formatSlot = (slot) => {
    if (!slot) return null;
    try {
      const date = new Date(slot);
      return format(date, 'EEEE, MMMM d, yyyy \'at\' h:mm a');
    } catch (e) {
      return slot;
    }
  };

  const handleConfirm = async () => {
    setIsConfirming(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    setIsConfirming(false);
    setIsConfirmed(true);
    
    if (onConfirm) {
      onConfirm(appointment);
    }
  };

  if (isConfirmed) {
    return (
      <div className="confirmation-card confirmed">
        <div className="success-animation">
          <div className="checkmark-circle">
            <div className="checkmark">✓</div>
          </div>
        </div>
        <h2>Appointment Confirmed!</h2>
        <div className="confirmed-details">
          <div className="detail-item">
            <span className="detail-label">Provider:</span>
            <span className="detail-value">{appointment.provider?.name}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Date & Time:</span>
            <span className="detail-value">{formatSlot(appointment.slot)}</span>
          </div>
          {appointment.provider?.phone && (
            <div className="detail-item">
              <span className="detail-label">Phone:</span>
              <span className="detail-value">{appointment.provider.phone}</span>
            </div>
          )}
        </div>
        <p className="confirmation-message">
          You will receive a confirmation email shortly.
        </p>
        {onCancel && (
          <button className="back-button" onClick={onCancel}>
            Book Another Appointment
          </button>
        )}
      </div>
    );
  }

  const provider = appointment.provider || {};

  return (
    <div className="confirmation-card">
      <h2>Confirm Appointment</h2>
      <div className="appointment-summary">
        <div className="summary-section">
          <h3>{provider.name}</h3>
          {provider.rating && (
            <div className="provider-meta">
              <span>⭐ {provider.rating.toFixed(1)}/5.0</span>
              {provider.distance_miles && (
                <span>📍 {provider.distance_miles.toFixed(1)} miles away</span>
              )}
            </div>
          )}
        </div>

        <div className="summary-section">
          <div className="appointment-time">
            <div className="time-label">Appointment Time</div>
            <div className="time-value">{formatSlot(appointment.slot)}</div>
          </div>
        </div>

        {appointment.score !== undefined && (
          <div className="summary-section">
            <div className="score-info">
              Match Score: <strong>{appointment.score.toFixed(2)}</strong>
            </div>
          </div>
        )}
      </div>

      <div className="confirmation-actions">
        <button
          className="confirm-button"
          onClick={handleConfirm}
          disabled={isConfirming}
        >
          {isConfirming ? 'Confirming...' : 'Confirm Booking'}
        </button>
        {onCancel && (
          <button className="cancel-button" onClick={onCancel} disabled={isConfirming}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
};

export default ConfirmationCard;
