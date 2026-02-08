import React, { useEffect, useState } from 'react';
import ProviderCard from './ProviderCard';
import './SwarmVisualization.css';

const SwarmVisualization = ({ providers, results, isActive }) => {
  const [providerStates, setProviderStates] = useState({});

  useEffect(() => {
    // Initialize provider states
    if (providers && providers.length > 0) {
      const initialStates = {};
      providers.forEach((provider) => {
        initialStates[provider.name] = {
          status: 'waiting',
          result: null,
        };
      });
      setProviderStates(initialStates);
    }
  }, [providers]);

  useEffect(() => {
    // Update provider states when results come in
    if (results) {
      setProviderStates((prev) => {
        const updated = { ...prev };
        
        results.forEach((result) => {
          const providerName = result.provider?.name;
          if (providerName) {
            updated[providerName] = {
              status: result.status || 'waiting',
              result: result,
            };
          }
        });
        
        return updated;
      });
    }
  }, [results]);

  if (!providers || providers.length === 0) {
    return (
      <div className="swarm-visualization empty">
        {isActive ? (
          <div className="finding-providers">
            <div className="finding-spinner" />
            <p>Finding nearby providers...</p>
          </div>
        ) : (
          <p>No providers to call</p>
        )}
      </div>
    );
  }

  const completedCount = Object.values(providerStates).filter(
    (state) => state.status !== 'waiting' && state.status !== 'calling'
  ).length;

  const totalCount = providers.length;

  return (
    <div className="swarm-visualization">
      <div className="swarm-header">
        <h2>Swarm Call Progress</h2>
        <div className="progress-indicator">
          <span className="progress-text">
            {completedCount} of {totalCount} calls completed
          </span>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${(completedCount / totalCount) * 100}%` }}
            />
          </div>
        </div>
      </div>

      <div className="provider-grid">
        {providers.length > 0 ? (
          providers.map((provider) => {
            const state = providerStates[provider.name] || {
              status: 'waiting',
              result: null,
            };
            
            // Determine status
            let status = state.status;
            if (isActive && status === 'waiting') {
              status = 'calling';
            }

            return (
              <ProviderCard
                key={provider.name || Math.random()}
                provider={provider}
                result={state.result}
                status={status}
              />
            );
          })
        ) : (
          <div className="no-providers">
            <p>Loading providers...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SwarmVisualization;
