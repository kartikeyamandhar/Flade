import React, { useEffect, useState, useCallback } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import { getGraphStats, getGraphData, GraphData } from '../../services/api';
import './GraphViz.css';

interface Props {
  documentId: string;
  isReady: boolean;
}

const GraphViz: React.FC<Props> = ({ documentId, isReady }) => {
  const [stats, setStats] = useState<any>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isReady) {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        // Get stats
        const statsData = await getGraphStats(documentId);
        setStats(statsData);

        // Get graph data for visualization
        const data = await getGraphData(documentId, 100);
        setGraphData(data);
        
        setLoading(false);
      } catch (err) {
        console.error('Failed to fetch graph:', err);
        setLoading(false);
      }
    };

    fetchData();
  }, [documentId, isReady]);

  const handleNodeClick = useCallback((node: any) => {
    console.log('Clicked node:', node.name);
  }, []);

  return (
    <div className="graph-viz">
      <div className="graph-header">
        <h3>🕸️ Knowledge Graph</h3>
        {stats && (
          <div className="graph-stats-mini">
            <div className="stat-mini">
              <span className="stat-value">{stats.total_nodes}</span>
              <span className="stat-label">Nodes</span>
            </div>
            <div className="stat-mini">
              <span className="stat-value">{stats.total_relationships}</span>
              <span className="stat-label">Links</span>
            </div>
          </div>
        )}
      </div>

      <div className="graph-container">
        {loading ? (
          <div className="graph-loading">
            <div className="spinner"></div>
            <p>Loading graph...</p>
          </div>
        ) : !isReady ? (
          <div className="graph-placeholder">
            <div className="placeholder-icon">🔄</div>
            <p>Processing document...</p>
            <p className="placeholder-note">Graph will appear when ready</p>
          </div>
        ) : graphData ? (
          <ForceGraph3D
            graphData={graphData}
            nodeLabel="name"
            nodeAutoColorBy="id"
            nodeVal={3}
            linkLabel="type"
            linkWidth={1}
            linkDirectionalParticles={2}
            linkDirectionalParticleSpeed={0.005}
            backgroundColor="#0f0f1e"
            onNodeClick={handleNodeClick}
            enableNodeDrag={true}
            enableNavigationControls={true}
          />
        ) : (
          <div className="graph-error">
            <p>No graph data available</p>
          </div>
        )}
      </div>

      {stats && (
        <div className="graph-legend">
          <h4>Relationship Types</h4>
          <div className="legend-items">
            {Object.entries(stats.relationship_types || {}).slice(0, 5).map(([type, count]) => (
              <div key={type} className="legend-item">
                <span className="legend-dot"></span>
                <span className="legend-text">{type}</span>
                <span className="legend-count">({count as number})</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GraphViz;
