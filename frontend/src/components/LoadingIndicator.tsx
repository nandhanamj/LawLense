import React from 'react';
import { Scale, Loader2 } from 'lucide-react';

export const LoadingIndicator: React.FC = () => {
  return (
    <article
      className="chat-row assistant-row loading-row"
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label="LawLens is reviewing the BNS corpus"
    >
      <div className="avatar assistant-avatar" aria-hidden="true">
        <Scale size={20} />
      </div>

      <div className="message-card assistant-card loading-card">
        <div className="loading-content">
          <Loader2 className="loading-spinner" size={20} aria-hidden="true" />
          <div className="loading-text-group">
            <p className="loading-primary-text">
              LawLens is reviewing the BNS corpus...
            </p>
            <p className="loading-secondary-text">
              Retrieving statutory provisions and verifying legal citations
            </p>
          </div>
        </div>
      </div>
    </article>
  );
};
