import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Copy, Check, BookOpen, Quote } from 'lucide-react';
import type { Citation } from '../types';

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export const CitationCard: React.FC<CitationCardProps> = ({ citation, index }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);

  const actName = citation.act || 'BNS';
  const sectionNum = citation.section;
  const sectionTitle = citation.title || 'Statutory Provision';
  const evidenceText = citation.supporting_text || citation.evidence || '';
  const sourceInfo =
    citation.source_info || citation.source || 'Bharatiya Nyaya Sanhita, 2023 (BNS)';

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const copyPayload = `${actName} Section ${sectionNum}: ${sectionTitle}\n"${evidenceText}"\nSource: ${sourceInfo}`;
    try {
      await navigator.clipboard.writeText(copyPayload);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback if clipboard API is restricted
    }
  };

  return (
    <article className="citation-card" aria-label={`Citation: ${actName} Section ${sectionNum}`}>
      <header
        className="citation-card-header"
        onClick={() => setIsExpanded((prev) => !prev)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsExpanded((prev) => !prev);
          }
        }}
        tabIndex={0}
        role="button"
        aria-expanded={isExpanded}
        aria-controls={`citation-body-${index}`}
      >
        <div className="citation-header-left">
          <div className="citation-tag">
            <BookOpen size={13} aria-hidden="true" />
            <span>{actName} · Section {sectionNum}</span>
          </div>
          <h4 className="citation-title">{sectionTitle}</h4>
        </div>

        <div className="citation-header-actions">
          <button
            type="button"
            className="citation-action-btn"
            onClick={handleCopy}
            title="Copy citation to clipboard"
            aria-label={`Copy citation for Section ${sectionNum}`}
          >
            {copied ? (
              <span className="copied-state">
                <Check size={14} aria-hidden="true" />
                <span>Copied</span>
              </span>
            ) : (
              <Copy size={14} aria-hidden="true" />
            )}
          </button>

          <span className="citation-toggle-icon" aria-hidden="true">
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </span>
        </div>
      </header>

      {isExpanded && (
        <div id={`citation-body-${index}`} className="citation-card-body">
          {evidenceText ? (
            <div className="citation-evidence-block">
              <div className="citation-evidence-label">
                <Quote size={13} aria-hidden="true" />
                <span>Statutory Evidence</span>
              </div>
              <blockquote className="citation-evidence-text">
                {evidenceText}
              </blockquote>
            </div>
          ) : (
            <div className="citation-evidence-placeholder">
              Verified provision in Bharatiya Nyaya Sanhita, 2023.
            </div>
          )}

          {sourceInfo && (
            <footer className="citation-source-footer">
              <span className="citation-source-label">Source:</span>{' '}
              <span className="citation-source-value">{sourceInfo}</span>
            </footer>
          )}
        </div>
      )}
    </article>
  );
};
