import React from 'react';
import './Header.css';

interface HeaderProps {
  onReset?: () => void;
  hasDocument?: boolean;
}

const Header: React.FC<HeaderProps> = ({ onReset, hasDocument }) => {
  const handleNewDocument = () => {
    if (window.confirm('Start a new document? This will clear the current session.')) {
      if (onReset) {
        onReset();
      }
      window.location.reload();
    }
  };

  return (
    <header className="header">
      <div className="header-content">
        <h1 className="header-title">Flade</h1>
        
        {hasDocument && (
          <button onClick={handleNewDocument} className="new-doc-button">
            📄 New Document
          </button>
        )}
      </div>
    </header>
  );
};

export default Header;