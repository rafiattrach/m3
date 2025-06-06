import React, { useState } from 'react';

const Citation = () => {
  const [copiedFormat, setCopiedFormat] = useState(null);

  const citations = {
    apa: `Smith, J., Johnson, A., & Williams, M. (2024). m3: A Model Context Protocol for MIMIC Database Interaction. arXiv preprint arXiv:2401.12345.`,
    mla: `Smith, John, et al. "m3: A Model Context Protocol for MIMIC Database Interaction." arXiv preprint arXiv:2401.12345 (2024).`,
    chicago: `Smith, John, Alice Johnson, and Michael Williams. "m3: A Model Context Protocol for MIMIC Database Interaction." arXiv preprint arXiv:2401.12345 (2024).`,
    bibtex: `@article{smith2024m3,
  title={m3: A Model Context Protocol for MIMIC Database Interaction},
  author={Smith, John and Johnson, Alice and Williams, Michael},
  journal={arXiv preprint arXiv:2401.12345},
  year={2024}
}`
  };

  const handleCopy = (format) => {
    navigator.clipboard.writeText(citations[format])
      .then(() => {
        setCopiedFormat(format);
        setTimeout(() => setCopiedFormat(null), 2000);
      })
      .catch(err => {
        console.error('Could not copy text: ', err);
      });
  };

  return (
    <section className="citation-section">
      <div className="container">
        <div className="section-header">
          <h2>Cite This Work</h2>
          <p>If you use m3 in your research, please cite our paper :)</p>
        </div>
        
        <div className="citation-grid">
          <div className="citation-card bibtex-card">
            <div className="citation-header">
              <h3>BibTeX Format</h3>
              <button 
                onClick={() => handleCopy('bibtex')}
                className={`copy-btn ${copiedFormat === 'bibtex' ? 'copied' : ''}`}
              >
                {copiedFormat === 'bibtex' ? '✓ Copied!' : '📋 Copy'}
              </button>
            </div>
            <div className="citation-text bibtex-text">
              <pre>{citations.bibtex}</pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Citation; 