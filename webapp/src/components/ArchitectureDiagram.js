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
          <img
            src="/m3/m3_architecture.png"
            alt="m3 Architecture Diagram"
            style={{
              width: '80%',
              maxWidth: '800px',
              height: 'auto',
              display: 'block',
              margin: '0 auto'
            }}
          />
        </div>
      </div>
    </section>
  );
};

export default ArchitectureDiagram;
