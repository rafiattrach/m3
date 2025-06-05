import React from 'react';

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
            <svg width="100%" height="300" viewBox="0 0 600 300" style={{background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)'}}>
              <rect width="100%" height="100%" fill="url(#dashboardGradient)"/>
              <defs>
                <linearGradient id="dashboardGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style={{stopColor:'#f8fafc'}}/>
                  <stop offset="100%" style={{stopColor:'#e2e8f0'}}/>
                </linearGradient>
              </defs>
              <rect x="20" y="20" width="560" height="40" rx="8" fill="white" stroke="#e2e8f0"/>
              <text x="40" y="45" fontFamily="Arial" fontSize="16" fontWeight="600" fill="#1a1a1a">m3 MIMIC Dashboard</text>
              <rect x="30" y="80" width="130" height="80" rx="8" fill="white" stroke="#e2e8f0"/>
              <text x="40" y="100" fontFamily="Arial" fontSize="12" fill="#64748b">MIMIC-IV Records</text>
              <text x="40" y="125" fontFamily="Arial" fontSize="24" fontWeight="700" fill="#1a1a1a">382,278</text>
              <text x="40" y="145" fontFamily="Arial" fontSize="12" fill="#10b981">Hospital admissions</text>

              <rect x="180" y="80" width="130" height="80" rx="8" fill="white" stroke="#e2e8f0"/>
              <rect x="190" y="120" width="110" height="30" rx="4" fill="#0052ff" opacity="0.8"/>

              <rect x="330" y="80" width="130" height="80" rx="8" fill="white" stroke="#e2e8f0"/>
              <text x="340" y="100" fontFamily="Arial" fontSize="12" fill="#64748b">Active Connections</text>
              <text x="340" y="125" fontFamily="Arial" fontSize="24" fontWeight="700" fill="#1a1a1a">1,247</text>
              <text x="340" y="145" fontFamily="Arial" fontSize="12" fill="#10b981">Researchers online</text>

              <rect x="480" y="80" width="100" height="80" rx="8" fill="white" stroke="#e2e8f0"/>
              <rect x="490" y="120" width="80" height="30" rx="4" fill="#00d4ff" opacity="0.8"/>
            </svg>
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
              <text x="20" y="195" fontFamily="Courier New" fontSize="14" fill="#f6ad55">    "SELECT * FROM patients WHERE age > 65"</text>
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
            <svg width="100%" height="300" viewBox="0 0 600 300" style={{background: 'white'}}>
              <rect width="100%" height="100%" fill="white" stroke="#e2e8f0"/>

              <text x="300" y="30" fontFamily="Arial" fontSize="16" fontWeight="600" fill="#1a1a1a" textAnchor="middle">ICU Length of Stay Distribution</text>

              <rect x="100" y="60" width="400" height="200" fill="none" stroke="#e2e8f0"/>

              <rect x="120" y="180" width="40" height="60" fill="#0052ff" opacity="0.8"/>
              <rect x="180" y="140" width="40" height="100" fill="#0052ff" opacity="0.8"/>
              <rect x="240" y="100" width="40" height="140" fill="#0052ff" opacity="0.8"/>
              <rect x="300" y="120" width="40" height="120" fill="#0052ff" opacity="0.8"/>
              <rect x="360" y="160" width="40" height="80" fill="#0052ff" opacity="0.8"/>
              <rect x="420" y="200" width="40" height="40" fill="#0052ff" opacity="0.8"/>

              <text x="140" y="275" fontFamily="Arial" fontSize="12" fill="#64748b" textAnchor="middle">1-2</text>
              <text x="200" y="275" fontFamily="Arial" fontSize="12" fill="#64748b" textAnchor="middle">3-5</text>
              <text x="260" y="275" fontFamily="Arial" fontSize="12" fill="#64748b" textAnchor="middle">6-10</text>
              <text x="320" y="275" fontFamily="Arial" fontSize="12" fill="#64748b" textAnchor="middle">11-15</text>
              <text x="380" y="275" fontFamily="Arial" fontSize="12" fill="#64748b" textAnchor="middle">16-20</text>
              <text x="440" y="275" fontFamily="Arial" fontSize="12" fill="#64748b" textAnchor="middle">20+</text>

              <text x="300" y="295" fontFamily="Arial" fontSize="14" fill="#1a1a1a" textAnchor="middle">Days in ICU</text>
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Explanation;
