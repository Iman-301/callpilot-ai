import React from 'react';
import './ServiceSelection.css';

const ServiceSelection = ({ value, onChange }) => {
  const services = [
    { value: 'dentist', label: 'Dentist' },
    { value: 'auto_repair', label: 'Auto Repair' },
    { value: 'doctor', label: 'Doctor' },
    { value: 'hairdresser', label: 'Hairdresser' },
    { value: 'other', label: 'Other' },
  ];

  return (
    <div className="service-selection">
      <label className="input-label">Service Type</label>
      <div className="service-options">
        {services.map((service) => (
          <button
            key={service.value}
            type="button"
            className={`service-option ${value === service.value ? 'active' : ''}`}
            onClick={() => onChange(service.value)}
          >
            {service.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default ServiceSelection;
