import React, { useState } from 'react';

const Hero = () => {
  const [isCopied, setIsCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText('pip install m3-mcp')
      .then(() => {
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
      })
      .catch(err => {
        console.error('Failed to copy: ', err);
      });
  };

  const handleScroll = (id) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section className="hero">
      <div className="container">
        <div className="hero-content">
          <div className="hero-text">
            <h1>Hello, Researchers!<br />Meet m3</h1>
            <p className="subtitle">m3 is a powerful Model Context Protocol for seamless interaction with the MIMIC database</p>
            <p className="description">Free and open-source tool that enables researchers to query and analyze the world's largest publicly available healthcare database with ease</p>
            <div className="hero-cta-group">
              <button onClick={() => handleScroll('paper')} className="cta-button">
                <span>📄</span> Read Paper
              </button>
              <button onClick={copyToClipboard} className="cta-button-secondary">
                <span role="img" aria-label={isCopied ? 'check mark' : 'laptop'}>
                  {isCopied ? '✅' : '💻'}
                </span>
                {isCopied ? 'Copied!' : 'pip install m3-mcp'}
              </button>
            </div>
          </div>
          <div className="hero-visual">
            <div className="laptop-mockup">
              <div className="laptop-frame">
                <div className="laptop-screen">
                  <div className="screen-content">
                    <div className="app-header">
                      <div className="traffic-lights">
                        <div className="traffic-light red"></div>
                        <div className="traffic-light yellow"></div>
                        <div className="traffic-light green"></div>
                      </div>
                      <div className="app-title">m3 MIMIC Dashboard</div>
                    </div>
                    <div className="dashboard-content">
                      <div className="dashboard-card">
                        <div className="card-header">Patients Queried</div>
                        <div className="card-value">38,542</div>
                        <div className="card-change">+1.2k this month</div>
                      </div>
                      <div className="dashboard-card">
                        <div className="card-header">Query Performance</div>
                        <div className="chart-placeholder"></div>
                      </div>
                      <div className="dashboard-card">
                        <div className="card-header">Active Researchers</div>
                        <div className="card-value">1,245</div>
                        <div className="card-change">+6.1% this month</div>
                      </div>
                      <div className="dashboard-card">
                        <div className="card-header">Data Throughput</div>
                        <div className="chart-placeholder"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
