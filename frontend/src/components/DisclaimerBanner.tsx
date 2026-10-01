import React from 'react';
import { ShieldAlert } from 'lucide-react';

export const DisclaimerBanner: React.FC = () => {
  return (
    <aside className="persistent-disclaimer" aria-label="Legal Notice">
      <div className="disclaimer-inner">
        <ShieldAlert size={14} className="disclaimer-icon" aria-hidden="true" />
        <p className="disclaimer-content">
          <strong>Legal Information Notice:</strong> LawLens provides objective legal
          information grounded in the Bharatiya Nyaya Sanhita, 2023 (BNS). It does not
          provide formal legal advice or advocate-client representation.
        </p>
      </div>
    </aside>
  );
};
