import React from 'react';

const Features = () => {
  return (
    <section className="features-section" id="features">
      <div className="container">
        <div className="section-header fade-in">
          <h2>Built for healthcare research</h2>
          <p>Everything researchers need to efficiently work with large-scale medical databases</p>
        </div>

        <div className="features-grid">
          <div className="feature-item fade-in">
            <div className="feature-icon">🏥</div>
            <h3>MIMIC Integration</h3>
            <p>Native support for the MIMIC-IV database with optimized queries and seamless data access patterns.</p>
          </div>

          <div className="feature-item fade-in">
            <div className="feature-icon">🔬</div>
            <h3>Research-Focused</h3>
            <p>Purpose-built for academic and clinical research with features tailored to healthcare data analysis workflows.</p>
          </div>

          <div className="feature-item fade-in">
            <div className="feature-icon">⚡</div>
            <h3>High Performance</h3>
            <p>Optimized query processing and intelligent caching for fast access to millions of medical records.</p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Features;
