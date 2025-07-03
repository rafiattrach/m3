import React from 'react';

const Paper = () => {
  return (
    <section className="paper-section" id="paper">
      <div className="container">
        <div className="section-header fade-in">
          <h2>Research Paper</h2>
          <p>Read our comprehensive study on the m3 Model Context Protocol and its applications in healthcare data analysis</p>
        </div>

        <div className="paper-preview fade-in" onClick={() => window.open('https://arxiv.org/abs/2507.01053', '_blank')}>
          <div className="paper-header">
            <div className="arxiv-badge">arXiv</div>
            <div className="paper-id">2507.01053</div>
          </div>
          <h3 className="paper-title">Conversational LLMs Simplify Secure Clinical Data Access, Understanding, and Analysis</h3>
          <div className="paper-authors">Rafi Al Attrach, Pedro Moreira, Rajna Fani, Renato Umeton, Leo Anthony Celi</div>
          <div className="paper-abstract">
            As ever-larger clinical datasets become available, they have the potential to unlock unprecedented opportunities for medical research. Foremost among them is Medical Information Mart for Intensive Care (MIMIC-IV), the world's largest open-source EHR database. However, the inherent complexity of these datasets, particularly the need for sophisticated querying skills and the need to understand the underlying clinical settings, often presents a significant barrier to their effective use. M3 lowers the technical barrier to understanding and querying MIMIC-IV data. With a single command it retrieves MIMIC-IV from PhysioNet, launches a local SQLite instance (or hooks into the hosted BigQuery), and-via the Model Context Protocol (MCP)-lets researchers converse with the database in plain English. Ask a clinical question in natural language; M3 uses a language model to translate it into SQL, executes the query against the MIMIC-IV dataset, and returns structured results alongside the underlying query for verifiability and reproducibility. Demonstrations show that minutes of dialogue with M3 yield the kind of nuanced cohort analyses that once demanded hours of handcrafted SQL and relied on understanding the complexities of clinical workflows. By simplifying access, M3 invites the broader research community to mine clinical critical-care data and accelerates the translation of raw records into actionable insight.
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
