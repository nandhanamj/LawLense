import React from 'react';
import { Scale, BookOpen, ShieldCheck, Search, Sparkles, ArrowRight } from 'lucide-react';

interface HeroLandingProps {
  onSelectQuery: (query: string) => void;
}

const SUGGESTED_QUERIES = [
  {
    category: 'Exact Section',
    query: 'What is Section 103 of the BNS?',
    desc: 'Murder and statutory penalties',
  },
  {
    category: 'Offence Inquiry',
    query: 'What is the punishment for murder under BNS?',
    desc: 'Capital punishment and life imprisonment',
  },
  {
    category: 'Sexual Offences',
    query: 'Explain Section 69 of the BNS',
    desc: 'Deceitful means in sexual relations',
  },
  {
    category: 'Property Crimes',
    query: 'What constitutes theft under BNS?',
    desc: 'Definition, elements, and Section 303',
  },
  {
    category: 'Cheating & Fraud',
    query: 'What is the punishment for cheating under BNS?',
    desc: 'Fraudulent property delivery & Section 318',
  },
  {
    category: 'Statutory Safeguard',
    query: 'What is the punishment for evading arrest under BNS?',
    desc: 'Resistance and obstruction to lawful apprehension',
  },
];

export const HeroLanding: React.FC<HeroLandingProps> = ({ onSelectQuery }) => {
  return (
    <section className="hero-landing" aria-label="Welcome to LawLens">
      <div className="hero-emblem" aria-hidden="true">
        <Scale size={44} className="hero-scale-icon" />
      </div>

      <div className="hero-text-content">
        <p className="hero-eyebrow">BNS LEGAL RESEARCH WORKSPACE</p>
        <h2 className="hero-headline">Legal clarity, grounded in the BNS.</h2>
        <p className="hero-tagline">
          AI-powered legal information assistant based on the Bharatiya Nyaya Sanhita, 2023.
        </p>
      </div>

      <div className="hero-pillars">
        <div className="pillar-item">
          <Search size={18} className="pillar-icon" aria-hidden="true" />
          <div className="pillar-text">
            <strong>Legal RAG Search</strong>
            <span>Find relevant statutory provisions</span>
          </div>
        </div>

        <div className="pillar-item">
          <BookOpen size={18} className="pillar-icon" aria-hidden="true" />
          <div className="pillar-text">
            <strong>BNS Section Retrieval</strong>
            <span>Explore the 2023 statutory corpus</span>
          </div>
        </div>

        <div className="pillar-item">
          <ShieldCheck size={18} className="pillar-icon" aria-hidden="true" />
          <div className="pillar-text">
            <strong>Verified Citations</strong>
            <span>Answers linked to statutory evidence</span>
          </div>
        </div>

        <div className="pillar-item">
          <Sparkles size={18} className="pillar-icon" aria-hidden="true" />
          <div className="pillar-text">
            <strong>AI Legal Assistance</strong>
            <span>Ask clear questions in natural language</span>
          </div>
        </div>
      </div>

      <div className="suggested-section">
        <h3 className="suggested-heading">Suggested Legal Inquiries</h3>
        <p className="suggested-subheading">
          Select a prompt to explore the BNS statutory corpus:
        </p>

        <div className="suggested-grid">
          {SUGGESTED_QUERIES.map((item, idx) => (
            <button
              key={idx}
              type="button"
              className="suggested-card"
              onClick={() => onSelectQuery(item.query)}
              aria-label={`Ask: ${item.query}`}
            >
              <div className="suggested-card-header">
                <span className="suggested-category">{item.category}</span>
                <ArrowRight size={14} className="suggested-arrow" aria-hidden="true" />
              </div>
              <p className="suggested-query">{item.query}</p>
              <p className="suggested-desc">{item.desc}</p>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
};
