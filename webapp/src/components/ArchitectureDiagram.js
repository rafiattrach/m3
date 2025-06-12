import React from 'react';

const ArchitectureDiagram = () => {
  return (
    <section className="architecture-section">
      <div className="container">
        <div className="section-header fade-in">
          <h2>Architecture Overview</h2>
          <p>How m3 Model Context Protocol connects AI models to MIMIC-IV healthcare data</p>
        </div>

        <div className="architecture-diagram fade-in">
          <svg
            width="100%"
            height="500"
            viewBox="0 0 1000 500"
            className="architecture-svg"
            style={{ background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)', borderRadius: '15px' }}
          >
            <defs>
              {/* Gradients */}
              <linearGradient id="claudeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#ff6b6b" />
                <stop offset="100%" stopColor="#ee5a24" />
              </linearGradient>

              <linearGradient id="mcpGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#4ecdc4" />
                <stop offset="100%" stopColor="#44bd87" />
              </linearGradient>

              <linearGradient id="dataGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#a8e6cf" />
                <stop offset="100%" stopColor="#7fcdcd" />
              </linearGradient>

              {/* Arrow marker */}
              <marker id="arrowhead" markerWidth="10" markerHeight="7"
                refX="10" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#333" />
              </marker>

              {/* Drop shadow filter */}
              <filter id="dropshadow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="4" stdDeviation="3" floodColor="#000" floodOpacity="0.1"/>
              </filter>
            </defs>

            {/* Flow indicators at top */}
            <g className="flow-indicators">
              <circle cx="120" cy="40" r="20" fill="#ff6b6b" opacity="0.2" />
              <text x="120" y="46" textAnchor="middle" fontSize="12" fontWeight="bold" fill="#333">1</text>
              <text x="120" y="25" textAnchor="middle" fontSize="11" fill="#333">User Query</text>

              <circle cx="350" cy="40" r="20" fill="#4ecdc4" opacity="0.2" />
              <text x="350" y="46" textAnchor="middle" fontSize="12" fontWeight="bold" fill="#333">2</text>
              <text x="350" y="25" textAnchor="middle" fontSize="11" fill="#333">MCP Tools</text>

              <circle cx="580" cy="40" r="20" fill="#a8e6cf" opacity="0.2" />
              <text x="580" y="46" textAnchor="middle" fontSize="12" fontWeight="bold" fill="#333">3</text>
              <text x="580" y="25" textAnchor="middle" fontSize="11" fill="#333">Data Access</text>

              <circle cx="820" cy="40" r="20" fill="#6c5ce7" opacity="0.2" />
              <text x="820" y="46" textAnchor="middle" fontSize="12" fontWeight="bold" fill="#333">0</text>
              <text x="820" y="25" textAnchor="middle" fontSize="11" fill="#333">Setup</text>
            </g>

            {/* Claude Desktop */}
            <g className="claude-desktop">
              <rect x="50" y="100" width="140" height="100" rx="12"
                fill="url(#claudeGradient)" filter="url(#dropshadow)" />
              <text x="120" y="130" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">
                Claude Desktop
              </text>
              <text x="120" y="150" textAnchor="middle" fill="white" fontSize="11">
                MCP Client
              </text>
              <text x="120" y="170" textAnchor="middle" fill="white" fontSize="11">
                AI Assistant
              </text>
              <text x="120" y="185" textAnchor="middle" fill="white" fontSize="11">
                Interface
              </text>
            </g>

            {/* MCP Server */}
            <g className="mcp-server">
              <rect x="270" y="120" width="160" height="80" rx="12"
                fill="url(#mcpGradient)" filter="url(#dropshadow)" />
              <text x="350" y="145" textAnchor="middle" fill="white" fontSize="14" fontWeight="bold">
                m3 MCP Server
              </text>
              <text x="350" y="165" textAnchor="middle" fill="white" fontSize="11">
                Model Context Protocol
              </text>
              <text x="350" y="180" textAnchor="middle" fill="white" fontSize="11">
                Tools & Authentication
              </text>
            </g>

            {/* Data Sources */}
            <g className="data-sources">
              {/* Local SQLite */}
              <rect x="500" y="100" width="130" height="70" rx="10"
                fill="url(#dataGradient)" filter="url(#dropshadow)" />
              <text x="565" y="125" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">
                Local SQLite
              </text>
              <text x="565" y="145" textAnchor="middle" fill="white" fontSize="10">
                MIMIC-IV Demo
              </text>
              <text x="565" y="158" textAnchor="middle" fill="white" fontSize="10">
                Database
              </text>

              {/* BigQuery */}
              <rect x="500" y="180" width="130" height="70" rx="10"
                fill="url(#dataGradient)" filter="url(#dropshadow)" />
              <text x="565" y="205" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">
                Google BigQuery
              </text>
              <text x="565" y="225" textAnchor="middle" fill="white" fontSize="10">
                Full MIMIC-IV
              </text>
              <text x="565" y="238" textAnchor="middle" fill="white" fontSize="10">
                Cloud Database
              </text>
            </g>

            {/* m3 init command */}
            <g className="m3-init">
              <rect x="750" y="320" width="140" height="60" rx="10"
                fill="#6c5ce7" filter="url(#dropshadow)" />
              <text x="820" y="340" textAnchor="middle" fill="white" fontSize="12" fontWeight="bold">
                m3 init
              </text>
              <text x="820" y="355" textAnchor="middle" fill="white" fontSize="10">
                Download & Setup
              </text>
              <text x="820" y="370" textAnchor="middle" fill="white" fontSize="10">
                MIMIC Files
              </text>
            </g>

            {/* Connection arrows */}
            <g className="connections">
              {/* Claude to MCP */}
              <path d="M 190 150 L 270 150"
                stroke="#333" strokeWidth="2" fill="none"
                markerEnd="url(#arrowhead)" />
              <text x="230" y="135" textAnchor="middle" fontSize="10" fill="#333" fontWeight="bold">
                MCP Protocol
              </text>

              {/* MCP to SQLite */}
              <path d="M 430 140 L 500 135"
                stroke="#333" strokeWidth="2" fill="none"
                markerEnd="url(#arrowhead)" />
              <text x="465" y="125" textAnchor="middle" fontSize="10" fill="#333" fontWeight="bold">
                SQL
              </text>

              {/* MCP to BigQuery */}
              <path d="M 430 170 L 500 215"
                stroke="#333" strokeWidth="2" fill="none"
                markerEnd="url(#arrowhead)" />
              <text x="465" y="205" textAnchor="middle" fontSize="10" fill="#333" fontWeight="bold">
                BigQuery API
              </text>

              {/* m3 init to SQLite */}
              <path d="M 750 340 Q 700 280 630 135"
                stroke="#6c5ce7" strokeWidth="2" fill="none"
                markerEnd="url(#arrowhead)" strokeDasharray="5,5" />
              <text x="680" y="255" textAnchor="middle" fontSize="10" fill="#6c5ce7" fontWeight="bold">
                Setup DB
              </text>
            </g>

            {/* Available Tools Box */}
            <g className="tools-box">
              <rect x="50" y="280" width="350" height="160" rx="8"
                fill="rgba(255,255,255,0.95)" stroke="#4ecdc4" strokeWidth="2"
                filter="url(#dropshadow)" />
              <text x="225" y="305" textAnchor="middle" fontSize="13" fontWeight="bold" fill="#333">
                Available MCP Tools
              </text>

              <text x="70" y="325" fontSize="11" fill="#555">• execute_mimic_query(sql_query)</text>
              <text x="70" y="345" fontSize="11" fill="#555">• get_database_schema()</text>
              <text x="70" y="365" fontSize="11" fill="#555">• get_table_info(table_name)</text>
              <text x="70" y="385" fontSize="11" fill="#555">• get_icu_stays(patient_id, limit)</text>
              <text x="70" y="405" fontSize="11" fill="#555">• get_lab_results(patient_id, lab_item)</text>
              <text x="70" y="425" fontSize="11" fill="#555">• get_race_distribution(limit)</text>
            </g>
          </svg>
        </div>

        {/* Architecture explanation cards */}
        <div className="architecture-explanation fade-in">
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '30px',
            marginTop: '40px'
          }}>
            <div style={{
              background: 'white',
              padding: '30px',
              borderRadius: '15px',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)',
              textAlign: 'center',
              transition: 'transform 0.3s ease, box-shadow 0.3s ease'
            }}
            onMouseEnter={(e) => {
              e.target.style.transform = 'translateY(-5px)';
              e.target.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.15)';
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'translateY(0)';
              e.target.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.1)';
            }}>
              <div style={{ fontSize: '48px', marginBottom: '20px' }}>🔧</div>
              <h3 style={{ color: '#2c3e50', marginBottom: '15px', fontSize: '1.3rem', fontWeight: '600' }}>
                Setup with m3 init
              </h3>
              <p style={{ color: '#5a6c7d', lineHeight: '1.6', margin: '0' }}>
                Use <code style={{
                  background: '#f8f9fa',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontFamily: 'Courier New, monospace',
                  color: '#4ecdc4',
                  fontWeight: '600'
                }}>m3 init mimic-iv-demo</code> to automatically download and setup the MIMIC-IV demo database locally, or configure BigQuery access for the full dataset.
              </p>
            </div>

            <div style={{
              background: 'white',
              padding: '30px',
              borderRadius: '15px',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)',
              textAlign: 'center',
              transition: 'transform 0.3s ease, box-shadow 0.3s ease'
            }}
            onMouseEnter={(e) => {
              e.target.style.transform = 'translateY(-5px)';
              e.target.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.15)';
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'translateY(0)';
              e.target.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.1)';
            }}>
              <div style={{ fontSize: '48px', marginBottom: '20px' }}>🤖</div>
              <h3 style={{ color: '#2c3e50', marginBottom: '15px', fontSize: '1.3rem', fontWeight: '600' }}>
                AI Model Integration
              </h3>
              <p style={{ color: '#5a6c7d', lineHeight: '1.6', margin: '0' }}>
                Claude Desktop connects to the m3 MCP server through the Model Context Protocol, gaining access to specialized healthcare data tools.
              </p>
            </div>

            <div style={{
              background: 'white',
              padding: '30px',
              borderRadius: '15px',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)',
              textAlign: 'center',
              transition: 'transform 0.3s ease, box-shadow 0.3s ease'
            }}
            onMouseEnter={(e) => {
              e.target.style.transform = 'translateY(-5px)';
              e.target.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.15)';
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'translateY(0)';
              e.target.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.1)';
            }}>
              <div style={{ fontSize: '48px', marginBottom: '20px' }}>🔍</div>
              <h3 style={{ color: '#2c3e50', marginBottom: '15px', fontSize: '1.3rem', fontWeight: '600' }}>
                Secure Data Access
              </h3>
              <p style={{ color: '#5a6c7d', lineHeight: '1.6', margin: '0' }}>
                All queries are validated and authenticated. The MCP server provides safe, controlled access to MIMIC-IV data through specialized tools.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ArchitectureDiagram;
