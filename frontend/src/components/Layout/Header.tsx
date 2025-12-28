import React from 'react';
import './Header.css';

interface HeaderProps {
  onNewDocument?: () => void;
  showNewButton?: boolean;
}

const Header: React.FC<HeaderProps> = ({ onNewDocument, showNewButton = false }) => {
  return (
    <header className="app-header">
      <div className="header-logo">Flade</div>
      {showNewButton && (
        <button className="new-document-btn" onClick={onNewDocument}>
          📄 New Document
        </button>
      )}
    </header>
  );
};

export default Header;