import React, { useEffect, useRef } from 'react';

const Demos = () => {
  const videoContainersRef = useRef([]);
  const videos = [
    { url: 'm3_website_1.mp4', duration: '2:33 min' },
    { url: 'm3_website_2.mp4', duration: '1:18 min' },
    { url: 'm3_website_3.mp4', duration: '1:25 min' },
    { url: 'm3_website_4.mp4', duration: '5:49 min' },
  ];

  useEffect(() => {
    const loadVideo = (container, videoInfo) => {
      if (!container) return;

      const videoUrl = videoInfo.url;
      const videoPath = `/m3/videos/${videoUrl}`;
      const video = document.createElement('video');
      video.controls = false;
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

    videoContainersRef.current.forEach((container, index) => {
      loadVideo(container, videos[index]);
    });
  }, []);

  return (
    <section className="demo-section" id="demos">
      <div className="container">
        <div className="section-header fade-in">
          <h2>See m3 in action</h2>
          <p>Watch step-by-step tutorials to get started with m3 and MIMIC-IV medical data</p>
        </div>

        <div className="demo-grid">
          <div className="demo-card fade-in">
            <div className="video-container" ref={el => videoContainersRef.current[0] = el}>
              <div className="video-overlay">2:33 min</div>
              <div className="play-button"></div>
            </div>
            <div className="demo-content">
              <h3>1. Prerequisites Setup</h3>
              <p>Get PhysioNet credentials, set up Google Cloud Platform BigQuery, and create a new project. Learn where to find your project ID for MCP configuration.</p>
            </div>
          </div>

          <div className="demo-card fade-in">
            <div className="video-container" ref={el => videoContainersRef.current[1] = el}>
              <div className="video-overlay">1:18 min</div>
              <div className="play-button"></div>
            </div>
            <div className="demo-content">
              <h3>2. Installation Guide</h3>
              <p>Two ways to install m3: pip install m3-mcp from PyPI or clone from GitHub. Choose the method that works best for your setup.</p>
            </div>
          </div>

          <div className="demo-card fade-in">
            <div className="video-container" ref={el => videoContainersRef.current[2] = el}>
              <div className="video-overlay">1:25 min</div>
              <div className="play-button"></div>
            </div>
            <div className="demo-content">
              <h3>3a. Quick Start: Demo Dataset</h3>
              <p>Download the MIMIC-IV demo dataset, configure Claude Desktop for MCP, verify it's running, and run your first natural language queries.</p>
            </div>
          </div>

          <div className="demo-card fade-in">
            <div className="video-container" ref={el => videoContainersRef.current[3] = el}>
              <div className="video-overlay">5:49 min</div>
              <div className="play-button"></div>
            </div>
            <div className="demo-content">
              <h3>3b. Full Power: BigQuery Dataset</h3>
              <p>Configure with Google BigQuery project ID for full MIMIC-IV dataset. Explore other MCP clients for local privacy-focused setups with local models.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Demos; 