import React, { useEffect, useState } from 'react';
import { getGraphStats } from '../../services/api';
import './ContentSummary.css';

interface ContentSummaryProps {
  documentId: string;
  isReady: boolean;
}

interface ContentItem {
  name: string;
  type: string;
  description?: string;
}

const ContentSummary: React.FC<ContentSummaryProps> = ({ documentId, isReady }) => {
  const [content, setContent] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isReady) {
      setLoading(false);
      return;
    }

    const fetchContent = async () => {
      try {
        // Get graph stats
        const stats = await getGraphStats(documentId);
        
        // Fetch actual entities from Neo4j
        const response = await fetch(`http://localhost:8000/api/v1/graph/${documentId}/entities`);
        const entities = await response.json();
        
        setContent({ stats, entities });
        setLoading(false);
      } catch (err) {
        console.error('Error fetching content:', err);
        setLoading(false);
      }
    };

    fetchContent();
  }, [documentId, isReady]);

  if (loading) {
    return (
      <div className="content-summary">
        <div className="summary-loading">
          <div className="spinner"></div>
          <p>Analyzing content...</p>
        </div>
      </div>
    );
  }

  if (!isReady) {
    return (
      <div className="content-summary">
        <div className="summary-placeholder">
          <div className="placeholder-icon">📄</div>
          <p>Content summary will appear here</p>
        </div>
      </div>
    );
  }

  // Group entities by type
  const grouped = content?.entities?.reduce((acc: any, entity: any) => {
    const type = entity.type || 'Other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(entity);
    return acc;
  }, {}) || {};

  // Create human-readable sections
  const sections = [
    {
      title: 'Equipment & Devices',
      types: ['EQUIPMENT', 'COMPONENT', 'ACCESSORY'],
      icon: '🔧',
      color: '#2196F3'
    },
    {
      title: 'Key Features',
      types: ['FEATURE', 'SOFTWARE'],
      icon: '⭐',
      color: '#4CAF50'
    },
    {
      title: 'Safety Information',
      types: ['SAFETY_ITEM'],
      icon: '⚠️',
      color: '#F44336'
    },
    {
      title: 'Setup & Procedures',
      types: ['PROCEDURE'],
      icon: '📋',
      color: '#9C27B0'
    },
    {
      title: 'Specifications',
      types: ['SPECIFICATION', 'STANDARD'],
      icon: '📊',
      color: '#FFC107'
    },
    {
      title: 'Tools & Materials',
      types: ['TOOL', 'CONSUMABLE'],
      icon: '🛠️',
      color: '#FF5722'
    }
  ];

  return (
    <div className="content-summary">
      <div className="summary-header">
        <h3>What's Inside</h3>
        <p className="summary-subtitle">Quick overview of manual content</p>
      </div>

      <div className="summary-sections">
        {sections.map(section => {
          // Get all entities for this section
          const items = section.types
            .flatMap(type => grouped[type] || [])
            .slice(0, 5); // Show max 5 items per section

          const totalCount = section.types.reduce((sum, type) => 
            sum + (grouped[type]?.length || 0), 0
          );

          if (totalCount === 0) return null;

          return (
            <div key={section.title} className="content-section">
              <div className="section-header">
                <span className="section-icon">{section.icon}</span>
                <h4>{section.title}</h4>
                <span className="section-count">({totalCount})</span>
              </div>
              
              <div className="section-items">
                {items.map((item, idx) => (
                  <div key={idx} className="content-item">
                    <div className="item-bullet" style={{ backgroundColor: section.color }}/>
                    <span className="item-name">{item.name}</span>
                  </div>
                ))}
                {totalCount > 5 && (
                  <div className="more-items">
                    +{totalCount - 5} more...
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {content?.stats && (
        <div className="summary-footer">
          <div className="footer-stat">
            <span className="stat-value">{content.stats.total_nodes}</span>
            <span className="stat-label">Total Items</span>
          </div>
          <div className="footer-stat">
            <span className="stat-value">{content.stats.total_relationships}</span>
            <span className="stat-label">Connections</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ContentSummary;