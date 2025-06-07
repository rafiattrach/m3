import React from 'react';

const Paper = () => {
  return (
    <section className="paper-section" id="paper">
      <div className="container">
        <div className="section-header fade-in">
          <h2>Research Paper</h2>
          <p>Read our comprehensive study on the m3 Model Context Protocol and its applications in healthcare data analysis</p>
        </div>

        <div className="paper-preview fade-in" onClick={() => window.open('https://arxiv.org/abs/2401.12345', '_blank')}>
          <div className="paper-header">
            <div className="arxiv-badge">arXiv</div>
            <div className="paper-id">2401.12345</div>
          </div>
          <h3 className="paper-title">m3: A Novel Model Context Protocol for Efficient Interaction with Large-Scale Electronic Health Record Databases</h3>
          <div className="paper-authors">John Doe, Jane Smith, Robert Johnson, Maria Garcia</div>
          <div className="paper-abstract">
            We present m3, a novel Model Context Protocol designed to facilitate seamless interaction with the Medical Information Mart for Intensive Care (MIMIC) database. Our approach leverages advanced natural language processing techniques combined with structured query optimization to enable researchers to access and analyze healthcare data more efficiently. The protocol introduces a standardized interface that abstracts the complexity of the underlying database schema while maintaining the flexibility required for diverse research applications. Through comprehensive evaluation on real-world healthcare datasets, we demonstrate that m3 achieves significant improvements in query performance and user accessibility compared to existing methods...
          </div>
          <div className="paper-stats">
            <div className="paper-stat">
              <span>📅</span>
              <span>Submitted: Jan 2024</span>
            </div>
            <div className="paper-stat">
              <span>📊</span>
              <span>15 pages, 8 figures</span>
            </div>
            <div className="paper-stat">
              <span>🏷️</span>
              <span>cs.DB, cs.AI</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Paper;
