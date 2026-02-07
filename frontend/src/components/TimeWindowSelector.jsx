import React, { useState, useEffect } from 'react';
import './TimeWindowSelector.css';

const TimeWindowSelector = ({ value, onChange, busySlots = [] }) => {
  const [date, setDate] = useState(value?.date || '');
  const [startTime, setStartTime] = useState(value?.start || '09:00');
  const [endTime, setEndTime] = useState(value?.end || '17:00');

  useEffect(() => {
    if (date && startTime && endTime) {
      onChange({
        date,
        start: startTime,
        end: endTime,
      });
    }
  }, [date, startTime, endTime, onChange]);

  // Get tomorrow's date as default (ISO format)
  const getTomorrow = () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split('T')[0];
  };

  const defaultDate = date || getTomorrow();

  return (
    <div className="time-window-selector">
      <label className="input-label">Preferred Time Window</label>
      
      <div className="time-inputs">
        <div className="input-group">
          <label className="input-sublabel">Date</label>
          <input
            type="date"
            className="date-input"
            value={date || defaultDate}
            onChange={(e) => setDate(e.target.value)}
            min={getTomorrow()}
          />
        </div>

        <div className="input-group">
          <label className="input-sublabel">Start Time</label>
          <input
            type="time"
            className="time-input"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
          />
        </div>

        <div className="input-group">
          <label className="input-sublabel">End Time</label>
          <input
            type="time"
            className="time-input"
            value={endTime}
            onChange={(e) => setEndTime(e.target.value)}
          />
        </div>
      </div>

      {busySlots.length > 0 && (
        <div className="busy-slots-info">
          <span className="info-icon">ℹ️</span>
          <span>Your calendar shows {busySlots.length} busy slot(s) that will be avoided</span>
        </div>
      )}
    </div>
  );
};

export default TimeWindowSelector;
