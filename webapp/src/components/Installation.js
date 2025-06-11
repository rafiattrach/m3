import React, { useEffect, useRef } from 'react';

const Installation = () => {
  const videoContainerRef = useRef(null);

  useEffect(() => {
    const loadVideo = (container) => {
      if (!container) return;

      const videoUrl = 'm3_website_2.mp4';
      const videoPath = `/m3/videos/${videoUrl}`;
      const video = document.createElement('video');
      video.controls = true;
      video.autoplay = true;
      video.muted = true;
      video.loop = true;
      video.style.width = '100%';
      video.style.height = '100%';
      video.style.objectFit = 'cover';
      video.src = videoPath;

      video.onloadeddata = () => {
        container.innerHTML = '';
        container.appendChild(video);
        video.play().catch(error => console.error("Autoplay was prevented: ", error));
      };

      video.onerror = () => {
        container.innerHTML = `
          <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: #000; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; flex-direction: column; gap: 16px;">
              <div style="font-size: 48px;">🎥</div>
              <div>Video not found: ${videoUrl}</div>
              <div style="font-size: 14px; opacity: 0.7;">Place videos in <code>public/videos</code></div>
          </div>
        `;
      };
    };

    loadVideo(videoContainerRef.current);
  }, []);

  return (
    <section className="installation-section" id="installation">
      {/* Video Banner */}
      <div className="container" style={{ padding: '60px 0' }}>
        <div className="section-header">
          <h2>Installation Guide</h2>
          <p>Follow the steps below to get m3 up and running on your system.</p>
        </div>
        <div className="demo-card" style={{ maxWidth: '800px', margin: '0 auto' }}>
          <div className="video-container" ref={videoContainerRef}>
            <div className="video-overlay">1:18 min</div>
            <div className="play-button"></div>
          </div>
          <div className="demo-content">
            <h3>Watch the Installation Walkthrough</h3>
            <p>This video provides a step-by-step guide to installing the m3 protocol and connecting to the MIMIC database for the first time.</p>
          </div>
        </div>
      </div>

      {/* Installation Steps */}
      <div className="container" style={{ padding: '60px 0' }}>
        <div className="paper-preview" style={{ marginBottom: '40px' }}>
          <h3>Prerequisites</h3>
          <p>Before you begin, ensure you have the following installed on your system:</p>
          <ul className="explanation-features" style={{ marginTop: '20px' }}>
            <li>Python 3.10 or higher</li>
            <li>pip (Python package installer)</li>
            <li>Access to the MIMIC-IV database.</li>
          </ul>
        </div>

        <div className="paper-preview" style={{ marginBottom: '40px' }}>
          <h3>Option A: Install from PyPI (Recommended)</h3>
          <h4>Step 1: Create Virtual Environment</h4>
          <div className="code-snippet">
            <span className="comment"># Create virtual environment (recommended)</span><br/>
            python -m venv .venv<br/>
            source .venv/bin/activate  <span className="comment"># Windows: .venv\Scripts\activate</span>
          </div>
          <h4>Step 2: Install M3</h4>
          <div className="code-snippet">
            <span className="comment"># Install M3</span><br/>
            pip install m3-mcp
          </div>
        </div>

        <div className="paper-preview" style={{ marginBottom: '40px' }}>
          <h3>Option B: Install from Source</h3>
          <h4>Step 1: Clone and Navigate</h4>
          <div className="code-snippet">
            <span className="comment"># Clone the repository</span><br/>
            git clone https://github.com/rafiattrach/m3.git<br/>
            cd m3
          </div>
          <h4>Step 2: Create Virtual Environment</h4>
          <div className="code-snippet">
            <span className="comment"># Create virtual environment</span><br/>
            python -m venv .venv<br/>
            source .venv/bin/activate  <span className="comment"># Windows: .venv\Scripts\activate</span>
          </div>
          <h4>Step 3: Install M3</h4>
          <div className="code-snippet">
            <span className="comment"># Install M3</span><br/>
            pip install .
          </div>
        </div>
      </div>
    </section>
  );
};

export default Installation;
