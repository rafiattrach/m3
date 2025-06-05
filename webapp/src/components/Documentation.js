import React from 'react';

const Documentation = () => {
  return (
    <div className="container" style={{ paddingTop: '120px' }}>
      <div className="section-header">
        <h2>Documentation</h2>
        <p>Understanding the Model Context Protocol (m3)</p>
      </div>

      <div className="paper-preview" style={{ marginBottom: '40px' }}>
        <h3>What is the Model Context Protocol (m3)?</h3>
        <p>The Model Context Protocol (m3) is a powerful framework designed to streamline interaction with large-scale databases like MIMIC. It provides a standardized, efficient, and user-friendly way for researchers to query and analyze complex healthcare data without needing to write raw SQL. By leveraging a context-aware model, m3 understands your research goals and translates natural language or simplified commands into optimized database queries.</p>
      </div>

      <div className="paper-preview" style={{ marginBottom: '40px' }}>
        <h3>How It Works</h3>
        <p>The m3 protocol operates on a simple yet powerful principle: it maintains a "context" of your current analysis. This context includes the data you've already loaded, the variables you're interested in, and the patient cohort you're studying. When you issue a new command, m3 uses this context to interpret your request and fetch the relevant data efficiently. This approach minimizes redundant data loading and dramatically speeds up iterative analysis.</p>
        <ul className="explanation-features" style={{ marginTop: '20px' }}>
          <li><strong>Context-Aware Queries:</strong> Remembers your previous steps to inform the next ones.</li>
          <li><strong>Natural Language Processing:</strong> Allows you to write queries in plain English.</li>
          <li><strong>Optimized Performance:</strong> Intelligently caches data and optimizes query execution.</li>
          <li><strong>Extensible Framework:</strong> Can be adapted to other large-scale databases beyond MIMIC.</li>
        </ul>
      </div>

      <div className="section-header">
        <h3>Core Tools & Commands</h3>
        <p>The m3 ecosystem includes a suite of tools to facilitate your research workflow.</p>
      </div>

      <div className="explanation-grid">
        <div className="code-snippet" style={{ width: '100%' }}>
          <span className="comment"># 1. Connect to the database</span><br/>
          <span className="keyword">import</span> m3<br/>
          db = m3.connect("mimic-iv")<br/><br/>
          <span className="comment"># 2. Define a patient cohort</span><br/>
          cohort = db.cohort.define("sepsis_patients", from_criteria="sepsis == True")<br/><br/>
          <span className="comment"># 3. Load relevant data</span><br/>
          vitals = cohort.load_data("vitalsigns", time_window="first_24h")<br/><br/>
          <span className="comment"># 4. Run analysis</span><br/>
          mean_hr = vitals.analyze("heart_rate", "mean")<br/><br/>
          <span className="comment"># 5. Visualize results</span><br/>
          vitals.visualize("heart_rate", "line_chart")
        </div>
        <div className="explanation-text">
          <h3>Command-Line Interface (CLI)</h3>
          <p>The m3 CLI provides a powerful set of commands to manage your data, run analyses, and interact with the MIMIC database directly from your terminal.</p>
          <ul className="explanation-features">
            <li><pre>m3 connect</pre> - Establishes a connection to the database.</li>
            <li><pre>m3 define</pre> - Creates a new patient cohort from specific criteria.</li>
            <li><pre>m3 load</pre> - Loads data for a defined cohort.</li>
            <li><pre>m3 analyze</pre> - Performs statistical analysis on the loaded data.</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Documentation;
