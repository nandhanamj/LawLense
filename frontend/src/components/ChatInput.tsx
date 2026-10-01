import React, { useRef, useEffect } from 'react';
import { SendHorizontal, CornerDownLeft } from 'lucide-react';

interface ChatInputProps {
  query: string;
  onChange: (value: string) => void;
  onSubmit: (e?: React.FormEvent) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  query,
  onChange,
  onSubmit,
  isLoading,
  disabled = false,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea according to input content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      // Cap at 160px height
      textareaRef.current.style.height = `${Math.min(scrollHeight, 160)}px`;
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (query.trim() && !isLoading && !disabled) {
        onSubmit();
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading && !disabled) {
      onSubmit(e);
    }
  };

  return (
    <footer className="chat-input-wrapper" role="region" aria-label="Legal Inquiry Input">
      <div className="chat-input-container">
        <form onSubmit={handleSubmit} className="chat-input-form">
          <div className="input-box-wrapper">
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              placeholder="Ask about the Bharatiya Nyaya Sanhita, 2023 (e.g., What does Section 103 provide?)..."
              value={query}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading || disabled}
              rows={1}
              aria-label="Legal question input"
              autoFocus
            />

            <button
              type="submit"
              className="send-button"
              disabled={!query.trim() || isLoading || disabled}
              aria-label={isLoading ? 'Reviewing legal corpus...' : 'Send legal question'}
              title="Submit legal inquiry"
            >
              <SendHorizontal size={18} aria-hidden="true" />
            </button>
          </div>

          <div className="input-metadata-row">
            <span className="input-shortcut-hint">
              <CornerDownLeft size={11} aria-hidden="true" />
              <span>Press <strong>Enter</strong> to submit, <strong>Shift + Enter</strong> for new line</span>
            </span>
            <span className="input-scope-tag">
              Scope: BNS 2023 (358 Sections)
            </span>
          </div>
        </form>
      </div>
    </footer>
  );
};
