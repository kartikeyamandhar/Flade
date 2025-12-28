import React, { useEffect, useState } from 'react';
import { getGraphStats, queryDocument } from '../../services/api';
import './DocumentPanel.css';

interface Props {
  documentId: string;
  documentName: string;
  isReady: boolean;
  onQuestionClick: (question: string) => void;
}

const DocumentPanel: React.FC<Props> = ({ documentId, documentName, isReady, onQuestionClick }) => {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'entities' | 'suggestions'>('overview');

  useEffect(() => {
    if (!isReady) {
      setLoading(false);
      return;
    }

    const fetchStats = async () => {
      try {
        const data = await getGraphStats(documentId);
        setStats(data);
        setLoading(false);
      } catch (err) {
        console.error('Failed to fetch stats:', err);
        setLoading(false);
      }
    };

    fetchStats();
  }, [documentId, isReady]);

  const suggestedQuestions = [
    "What is this document about?",
    "What are the main features?",
    "List the key specifications",
    "What safety precautions are mentioned?",
    "Summarize the installation steps",
    "What tools are required?"
  ];

  const topEntities = stats?.node_types ? Object.keys(stats.node_types).slice(0, 8) : [];
  const relationshipTypes = stats?.relationship_types ? Object.entries(stats.relationship_types).slice(0, 6) : [];

  return (
    <div className="document-panel">
      <div className="panel-header">
        <div className="doc-icon">📄</div>
        <div className="doc-info">
          <h3 className="doc-title">{documentName}</h3>
          <span className="doc-status">{isReady ? '✓ Ready' : '⏳ Processing...'}</span>
        </div>
      </div>

      {loading ? (
        <div className="panel-loading">
          <div className="spinner-small"></div>
          <p>Loading document data...</p>
        </div>
      ) : !isReady ? (
        <div className="panel-placeholder">
          <div className="placeholder-icon">⚙️</div>
          <p>Processing document...</p>
          <p className="placeholder-note">Intelligence panel will appear when ready</p>
        </div>
      ) : (
        <>
          <div className="panel-tabs">
            <button 
              className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              Overview
            </button>
            <button 
              className={`tab ${activeTab === 'entities' ? 'active' : ''}`}
              onClick={() => setActiveTab('entities')}
            >
              Entities
            </button>
            <button 
              className={`tab ${activeTab === 'suggestions' ? 'active' : ''}`}
              onClick={() => setActiveTab('suggestions')}
            >
              Suggestions
            </button>
          </div>

          <div className="panel-content">
            {activeTab === 'overview' && stats && (
              <div className="overview-tab">
                <div className="stat-cards">
                  <div className="stat-card primary">
                    <div className="stat-number">{stats.total_nodes}</div>
                    <div className="stat-label">Entities Extracted</div>
                  </div>
                  <div className="stat-card secondary">
                    <div className="stat-number">{stats.total_relationships}</div>
                    <div className="stat-label">Connections Mapped</div>
                  </div>
                </div>

                <div className="section">
                  <h4 className="section-title">📊 Relationship Types</h4>
                  <div className="relationship-list">
                    {relationshipTypes.map(([type, count]: [string, any]) => (
                      <div key={type} className="relationship-item">
                        <span className="rel-type">{type}</span>
                        <span className="rel-count">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'entities' && (
              <div className="entities-tab">
                <div className="section">
                  <h4 className="section-title">🏷️ Extracted Entities</h4>
                  <div className="entity-grid">
                    {topEntities.map((entity) => (
                      <div key={entity} className="entity-badge">
                        {entity}
                      </div>
                    ))}
                  </div>
                  {topEntities.length === 0 && (
                    <p className="empty-state">No entities found</p>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'suggestions' && (
              <div className="suggestions-tab">
                <div className="section">
                  <h4 className="section-title">💡 Suggested Questions</h4>
                  <div className="question-list">
                    {suggestedQuestions.map((question, idx) => (
                      <button
                        key={idx}
                        className="question-suggestion"
                        onClick={() => onQuestionClick(question)}
                      >
                        <span className="question-icon">❓</span>
                        <span className="question-text">{question}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default DocumentPanel;