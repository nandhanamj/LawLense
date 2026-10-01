import React, { useState } from 'react';
import {
  Scale,
  User,
  ShieldCheck,
  AlertTriangle,
  Copy,
  Check,
  RotateCcw,
  BookOpen,
} from 'lucide-react';
import type { ChatMessage } from '../types';
import { CitationCard } from './CitationCard';

interface MessageBubbleProps {
  message: ChatMessage;
  onRetry?: (query: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onRetry }) => {
  const [copied, setCopied] = useState<boolean>(false);
  const isUser = message.role === 'user';
  const response = message.response;

  const handleCopyAnswer = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const formatTimestamp = (date: Date): string => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Render paragraphs cleanly from answer text
  const renderParagraphs = (text: string) => {
    const paragraphs = text
      .split(/\n{2,}/)
      .map((p) => p.trim())
      .filter(Boolean);

    return paragraphs.map((para, idx) => {
      // Preserve single line breaks within paragraphs
      const lines = para.split('\n');
      return (
        <p key={idx} className="message-paragraph">
          {lines.map((line, lineIdx) => (
            <React.Fragment key={lineIdx}>
              {line}
              {lineIdx < lines.length - 1 && <br />}
            </React.Fragment>
          ))}
        </p>
      );
    });
  };

  if (isUser) {
    return (
      <article className="chat-row user-row" aria-label="Your message">
        <div className="message-card user-card">
          <div className="message-header user-header">
            <span className="user-name">You</span>
            <time className="message-time">{formatTimestamp(message.timestamp)}</time>
          </div>
          <div className="message-body user-body">
            <p className="message-text">{message.content}</p>
          </div>
        </div>
        <div className="avatar user-avatar" aria-hidden="true">
          <User size={18} />
        </div>
      </article>
    );
  }

  // Assistant message
  const isRefusal = Boolean(response?.is_refusal || (response && !response.supported));
  const isError = Boolean(message.isError);
  const citations = response?.citations || [];

  return (
    <article className="chat-row assistant-row" aria-label="LawLens response">
      <div className="avatar assistant-avatar" aria-hidden="true">
        <Scale size={20} />
      </div>

      <div className="message-card assistant-card">
        <div className="message-header assistant-header">
          <div className="assistant-badge-group">
            <span className="assistant-name">LawLens</span>
            {response && !isRefusal && !isError && (
              <span className="verified-badge">
                <ShieldCheck size={13} aria-hidden="true" />
                <span>Verified BNS Grounding</span>
              </span>
            )}
            {isRefusal && (
              <span className="refusal-badge">
                <AlertTriangle size={13} aria-hidden="true" />
                <span>Statutory Scope Notice</span>
              </span>
            )}
          </div>

          <div className="assistant-actions">
            <time className="message-time">{formatTimestamp(message.timestamp)}</time>
            <button
              type="button"
              className="copy-answer-btn"
              onClick={handleCopyAnswer}
              title="Copy response to clipboard"
              aria-label="Copy response to clipboard"
            >
              {copied ? (
                <span className="copied-inline">
                  <Check size={13} aria-hidden="true" />
                  <span>Copied</span>
                </span>
              ) : (
                <Copy size={13} aria-hidden="true" />
              )}
            </button>
          </div>
        </div>

        {/* Refusal Callout */}
        {isRefusal && response?.refusal_reason && (
          <div className="refusal-banner" role="alert">
            <div className="refusal-banner-title">
              <AlertTriangle size={16} aria-hidden="true" />
              <span>Information Unavailable / Out of Scope</span>
            </div>
            <p className="refusal-banner-reason">{response.refusal_reason}</p>
          </div>
        )}

        {/* Error Callout */}
        {isError && (
          <div className="error-banner" role="alert">
            <div className="error-banner-title">
              <AlertTriangle size={16} aria-hidden="true" />
              <span>Service Connection Notice</span>
            </div>
            <p className="error-banner-text">{message.content}</p>
            {onRetry && (
              <button
                type="button"
                className="retry-btn"
                onClick={() => onRetry(message.content)}
              >
                <RotateCcw size={14} aria-hidden="true" />
                <span>Retry Query</span>
              </button>
            )}
          </div>
        )}

        {/* Answer Content */}
        {!isError && (
          <div className="message-body assistant-body">
            {renderParagraphs(message.content)}
          </div>
        )}

        {/* Citations List */}
        {!isRefusal && citations.length > 0 && (
          <section className="citations-section" aria-label="Verified Citations">
            <div className="citations-section-header">
              <div className="citations-heading-group">
                <BookOpen size={16} className="citations-heading-icon" aria-hidden="true" />
                <h3 className="citations-heading">Supporting Statutory Evidence</h3>
              </div>
              <span className="citations-count-badge">
                {citations.length} {citations.length === 1 ? 'Section' : 'Sections'}
              </span>
            </div>

            <div className="citations-grid">
              {citations.map((citation, idx) => (
                <CitationCard
                  key={`${citation.act}-${citation.section}-${idx}`}
                  citation={citation}
                  index={idx}
                />
              ))}
            </div>
          </section>
        )}

        {/* Legal Disclaimer */}
        <footer className="response-disclaimer-footer">
          <p className="disclaimer-text">
            <strong>Disclaimer:</strong> LawLens provides objective legal information from the
            statutory text of the Bharatiya Nyaya Sanhita, 2023 (BNS) and does not constitute formal legal advice.
          </p>
        </footer>
      </div>
    </article>
  );
};
