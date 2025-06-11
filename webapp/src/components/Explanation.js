import React from 'react';
import ArchitectureDiagram from './ArchitectureDiagram';

const Explanation = () => {
  return (
    <section className="explanation-section">
      <div className="container">
        <div className="section-header fade-in">
          <h2>Powerful features in action</h2>
          <p>See how m3 simplifies complex database interactions with intuitive interfaces</p>
        </div>

        {/* Dashboard Overview */}
        <div className="explanation-grid fade-in">
          <div className="explanation-text">
            <h3>Real-time MIMIC Database Dashboard</h3>
            <p>Monitor your database connections and query performance in real-time. The dashboard provides instant insights into MIMIC-IV records, active researcher connections, and system performance metrics.</p>
            <ul className="explanation-features">
              <li>Live connection monitoring</li>
              <li>Query performance analytics</li>
              <li>Database health indicators</li>
              <li>User activity tracking</li>
            </ul>
          </div>
          <div className="screenshot-container">
            <img src="m3/banner2.png" alt="Dashboard Overview" />
          </div>
        </div>

        {/* Query Interface */}
        <div className="explanation-grid fade-in">
          <div className="explanation-text">
            <h3>Intuitive Query Interface</h3>
            <p>Write complex MIMIC database queries using natural language or SQL. Our intelligent interface provides auto-completion, syntax highlighting, and query optimization suggestions.</p>
            <div className="code-snippet">
              <span className="comment"># Natural language query example</span><br/>
              <span className="keyword">import</span> m3<br/>
              <br/>
              <span className="comment"># Connect to MIMIC database</span><br/>
              db = m3.connect(<span className="string">"mimic-iv"</span>)<br/>
              <br/>
              <span className="comment"># Query ICU patients with specific conditions</span><br/>
              results = db.query(<span className="string">"Show me ICU patients with sepsis in 2019"</span>)
            </div>
            <ul className="explanation-features">
              <li>Natural language processing</li>
              <li>SQL auto-completion</li>
              <li>Query optimization</li>
              <li>Result visualization</li>
            </ul>
          </div>
          <div className="screenshot-container">
            <svg width="100%" height="300" viewBox="0 0 600 300" style={{background: '#1a1a1a'}}>
              <rect width="100%" height="100%" fill="#1a1a1a"/>
              <rect x="0" y="0" width="600" height="30" fill="#2d3748"/>
              <circle cx="15" cy="15" r="6" fill="#ff5f57"/>
              <circle cx="35" cy="15" r="6" fill="#ffbd2e"/>
              <circle cx="55" cy="15" r="6" fill="#28ca42"/>
              <text x="80" y="20" fontFamily="Arial" fontSize="12" fill="white">m3 Query Terminal</text>

              <text x="20" y="60" fontFamily="Courier New" fontSize="14" fill="#68d391"># Connect to MIMIC-IV</text>
              <text x="20" y="85" fontFamily="Courier New" fontSize="14" fill="#63b3ed">from</text>
              <text x="70" y="85" fontFamily="Courier New" fontSize="14" fill="white">m3</text>
              <text x="95" y="85" fontFamily="Courier New" fontSize="14" fill="#63b3ed">import</text>
              <text x="150" y="85" fontFamily="Courier New" fontSize="14" fill="white">Database</text>

              <text x="20" y="110" fontFamily="Courier New" fontSize="14" fill="white">db = Database(</text>
              <text x="120" y="110" fontFamily="Courier New" fontSize="14" fill="#f6ad55">"mimic-iv"</text>
              <text x="190" y="110" fontFamily="Courier New" fontSize="14" fill="white">)</text>

              <text x="20" y="145" fontFamily="Courier New" fontSize="14" fill="#68d391"># Query patient data</text>
              <text x="20" y="170" fontFamily="Courier New" fontSize="14" fill="white">results = db.query(</text>
              <text x="20" y="195" fontFamily="Courier New" fontSize="14" fill="#f6ad55">    "SELECT * FROM patients WHERE age &gt; 65"</text>
              <text x="20" y="220" fontFamily="Courier New" fontSize="14" fill="white">)</text>

              <rect x="20" y="240" width="2" height="18" fill="#0052ff">
                <animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/>
              </rect>
            </svg>
          </div>
        </div>

        {/* Data Visualization */}
        <div className="explanation-grid fade-in">
          <div className="explanation-text">
            <h3>Advanced Data Visualization</h3>
            <p>Transform complex medical data into clear, actionable insights with built-in visualization tools. Generate publication-ready charts and graphs directly from your queries.</p>
            <ul className="explanation-features">
              <li>Interactive charts and graphs</li>
              <li>Statistical analysis tools</li>
              <li>Export to multiple formats</li>
              <li>Publication-ready visualizations</li>
            </ul>
          </div>
          <div className="screenshot-container">
            <img src="m3/banner3.png" alt="Advanced Data Visualization" />
          </div>
        </div>
      </div>

      {/* Architecture Diagram */}
      <ArchitectureDiagram />
    </section>
  );
};

export default Explanation;
