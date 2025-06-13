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
          <h3 className="paper-title">M3-Mind the Gap: Democratizing EHR Access via MCP-Powered AI Agents</h3>
          <div className="paper-authors">Rafi Al Attrach, Pedro Moreira, Rajna Fani, Renato Umeton, Leo Anthony Celi</div>
          <div className="paper-abstract">
            The increasing availability of large-scale clinical databases offers unprecedented opportunities for medical research. However, the inherent complexity of these datasets, particularly the need for sophisticated querying skills, often presents a significant barrier to their effective utilization. The Medical Information Mart for Intensive Care (MIMIC-IV) is a vital resource in critical care research, yet its intricate structure traditionally demands proficiency in Structured Query Language (SQL). This paper introduces M3, a system designed to democratize access to MIMIC-IV by enabling researchers to query the database using natural language. M3 employs an AI-assisted approach, leveraging a Model Context Protocol (MCP) framework, and supports both SQLite and Google BigQuery for querying the full-scale MIMIC-IV dataset. Demonstrations have shown M3's capability to rapidly get deep, intricate insights into one of the biggest EHR databases. By simplifying data interaction, M3 has the potential to lower the technical threshold for medical data analysis, thereby facilitating broader research engagement and accelerating the generation of clinical insights.
          </div>
          <div className="paper-stats">
            <div className="paper-stat">
              <span>🏢</span>
              <span>MIT, TUM, UPF, St. Jude, BIDMC</span>
            </div>
            <div className="paper-stat">
              <span>🔗</span>
              <span>github.com/rafiattrach/m3</span>
            </div>
            <div className="paper-stat">
              <span>📦</span>
              <span>pypi.org/project/m3-mcp</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Paper;
