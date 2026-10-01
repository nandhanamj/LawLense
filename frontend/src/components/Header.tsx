import React from 'react';
import { Scale, RotateCcw, Sparkles } from 'lucide-react';

interface HeaderProps {
  onNewConversation: () => void;
  hasMessages: boolean;
  conversationId: string | null;
}

export const Header: React.FC<HeaderProps> = ({
  onNewConversation,
  hasMessages,
  conversationId,
}) => {
  return (
    <header className="site-header" role="banner">
      <div className="header-container">
        <div className="brand-group">
          <div className="brand-icon-wrapper" aria-hidden="true">
            <Scale className="brand-icon" size={24} />
          </div>
          <div className="brand-text">
            <div className="brand-title-row">
              <h1 className="brand-title">LawLens</h1>
              <span className="brand-badge">BNS 2023</span>
            </div>
            <p className="brand-subtitle">
              Bharatiya Nyaya Sanhita Legal Intelligence
            </p>
          </div>
        </div>

        <nav className="header-nav" aria-label="Current workspace">
          <span className="header-nav-item active" aria-current="page">
            <Sparkles size={15} aria-hidden="true" />
            <span>Legal assistant</span>
          </span>
        </nav>

        <div className="header-actions">
          {conversationId && (
            <div
              className="session-indicator"
              title={`Active Session: ${conversationId}`}
              aria-label="Active conversation session active"
            >
              <span className="session-dot" aria-hidden="true" />
              <span className="session-text">Session Active</span>
            </div>
          )}

          <button
            type="button"
            className="new-chat-btn"
            onClick={onNewConversation}
            disabled={!hasMessages && !conversationId}
            aria-label="Start a new conversation"
            title="Clear current conversation and start fresh"
          >
            <RotateCcw size={16} aria-hidden="true" />
            <span>New Conversation</span>
          </button>
        </div>
      </div>
    </header>
  );
};
