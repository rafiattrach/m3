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
            <img src="/m3/banner2.png" alt="Dashboard Overview" />
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
            <img src="/m3/banner3.png" alt="Advanced Data Visualization" />
          </div>
        </div>
      </div>

      {/* Architecture Diagram */}
      <ArchitectureDiagram />
    </section>
  );
};

export default Explanation;
