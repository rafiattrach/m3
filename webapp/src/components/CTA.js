import React from 'react';

const CTA = () => {
  return (
    <>
      <style>
        {`
          @keyframes float {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
            100% { transform: translateY(0px); }
          }

          @keyframes rotate {
              from {
                  transform: translateX(-50%) rotate(0deg);
              }
              to {
                  transform: translateX(-50%) rotate(360deg);
              }
          }

          .cta-content {
            animation: float 5s ease-in-out infinite;
          }

          .cta-section::before {
            animation: rotate 20s linear infinite;
          }
        `}
      </style>
      <section className="cta-section">
        <div className="container">
          <div className="cta-content">
            <h2>Contribute to our Open Source project</h2>
            <p>Help us build a better platform for everyone. We are looking for developers to contribute with their code and ideas.</p>
            <a href="https://github.com/rafiattrach/m3/issues" className="btn-contribute-cta">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" style={{ marginRight: '8px' }}>
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.108-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.91 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              Contribute Now
            </a>
          </div>
        </div>
      </section>
    </>
  );
};

export default CTA;
