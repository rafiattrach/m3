import React, { useState } from 'react';

const Citation = () => {
  const [copiedFormat, setCopiedFormat] = useState(null);

  const citations = {
    apa: `Al Attrach, R., Moreira, P., Fani, R., Umeton, R., & Celi, L. A. (2025). Conversational LLMs Simplify Secure Clinical Data Access, Understanding, and Analysis. arXiv preprint arXiv:2507.01053.`,
    mla: `Al Attrach, Rafi, et al. "Conversational LLMs Simplify Secure Clinical Data Access, Understanding, and Analysis." arXiv preprint arXiv:2507.01053 (2025).`,
    chicago: `Al Attrach, Rafi, Pedro Moreira, Rajna Fani, Renato Umeton, and Leo Anthony Celi. "Conversational LLMs Simplify Secure Clinical Data Access, Understanding, and Analysis." arXiv preprint arXiv:2507.01053 (2025).`,
    bibtex: `@misc{attrach2025conversationalllmssimplifysecure,
      title={Conversational LLMs Simplify Secure Clinical Data Access, Understanding, and Analysis},
      author={Rafi Al Attrach and Pedro Moreira and Rajna Fani and Renato Umeton and Leo Anthony Celi},
      year={2025},
      eprint={2507.01053},
      archivePrefix={arXiv},
      primaryClass={cs.IR},
      url={https://arxiv.org/abs/2507.01053},
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
