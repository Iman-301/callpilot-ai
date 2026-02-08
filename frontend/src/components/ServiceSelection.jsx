import React from 'react';
import { useLanguage } from '../contexts/LanguageContext';
import './ServiceSelection.css';

const ServiceSelection = ({ value, onChange }) => {
  const { t } = useLanguage();
  const services = [
    { value: 'dentist', label: t('services.dentist') },
    { value: 'auto_repair', label: 'Auto Repair' },
    { value: 'doctor', label: t('services.doctor') },
    { value: 'hairdresser', label: t('services.hairdresser') },
    { value: 'other', label: 'Other' },
  ];

  return (
    <div className="service-selection">
      <label className="input-label">{t('input.service')}</label>
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
