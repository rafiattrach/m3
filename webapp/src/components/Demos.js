import React from 'react';

const Demos = () => {
  const playVideo = (container) => {
    // A placeholder for video playback logic
    console.log('Playing video in:', container);
    container.innerHTML = `
      <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: #000; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; flex-direction: column; gap: 16px;">
          <div style="font-size: 48px;">🎥</div>
          <div>Demo video would play here</div>
          <div style="font-size: 14px; opacity: 0.7;">Replace with your actual video URL</div>
      </div>
    `;
  };

  return (
    <section className="demo-section" id="demos">
      <div className="container">
        <div className="section-header fade-in">
          <h2>See m3 in action</h2>
          <p>Watch how researchers are using m3 to unlock insights from the MIMIC database</p>
        </div>

        <div className="demo-grid">
          <div className="demo-card fade-in">
            <div className="video-container" onClick={(e) => playVideo(e.currentTarget)}>
              <div className="video-overlay">5:30 min</div>
              <div className="play-button"></div>
            </div>
            <div className="demo-content">
              <h3>Getting Started with m3</h3>
              <p>Learn how to install m3 and connect to the MIMIC database. This tutorial covers the basic setup and your first queries.</p>
            </div>
          </div>

          <div className="demo-card fade-in">
            <div className="video-container" onClick={(e) => playVideo(e.currentTarget)}>
              <div className="video-overlay">8:15 min</div>
              <div className="play-button"></div>
            </div>
            <div className="demo-content">
              <h3>Advanced Query Patterns</h3>
              <p>Explore complex queries and data analysis patterns using m3's powerful context protocol for healthcare research.</p>
            </div>
          </div>

          <div className="demo-card fade-in">
            <div className="video-container" onClick={(e) => playVideo(e.currentTarget)}>
              <div className="video-overlay">6:45 min</div>
              <div className="play-button"></div>
            </div>
            <div className="demo-content">
              <h3>Real-world Research Case Study</h3>
              <p>See how researchers used m3 to conduct a comprehensive study on ICU patient outcomes and treatment effectiveness.</p>
            </div>
          </div>

          <div className="demo-card fade-in">
            <div className="video-container" onClick={(e) => playVideo(e.currentTarget)}>
              <div className="video-overlay">4:20 min</div>
              <div className="play-button"></div>
            </div>
            <div className="demo-content">
              <h3>Performance Optimization</h3>
              <p>Learn best practices for optimizing query performance and handling large-scale healthcare datasets with m3.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Demos;
