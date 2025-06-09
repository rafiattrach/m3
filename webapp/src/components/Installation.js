import React from 'react';

const Installation = () => {
  const playVideo = (e) => {
    const container = e.currentTarget;
    // A placeholder for video playback logic
    console.log('Playing video in:', container);
    container.innerHTML = `
      <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: #000; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; flex-direction: column; gap: 16px;">
          <div style="font-size: 48px;">🎥</div>
          <div>Installation demo video would play here</div>
          <div style="font-size: 14px; opacity: 0.7;">Replace with your actual video URL</div>
      </div>
    `;
  };

  return (
    <div style={{ paddingTop: '80px' }}>
      {/* Video Banner */}
      <section className="demo-section" style={{ padding: '60px 0' }}>
        <div className="container">
          <div className="section-header">
            <h2>Installation Guide</h2>
            <p>Follow the steps below to get m3 up and running on your system.</p>
          </div>
          <div className="demo-card" style={{ maxWidth: '800px', margin: '0 auto' }}>
            <div className="video-container" onClick={playVideo}>
              <div className="video-overlay">2:30 min</div>
              <div className="play-button"></div>
            </div>
            <div className="demo-content">
              <h3>Watch the Installation Walkthrough</h3>
              <p>This video provides a step-by-step guide to installing the m3 protocol and connecting to the MIMIC database for the first time.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Installation Steps */}
      <section className="explanation-section" style={{ padding: '60px 0' }}>
        <div className="container">
          <div className="paper-preview" style={{ marginBottom: '40px' }}>
            <h3>Prerequisites</h3>
            <p>Before you begin, ensure you have the following installed on your system:</p>
            <ul className="explanation-features" style={{ marginTop: '20px' }}>
              <li>Python 3.8 or higher</li>
              <li>pip (Python package installer)</li>
              <li>Access to the MIMIC-IV database on BigQuery or a local PostgreSQL instance.</li>
            </ul>
          </div>

          <div className="paper-preview" style={{ marginBottom: '40px' }}>
            <h3>1. Installation via PyPI</h3>
            <p>The easiest way to install m3 is directly from the Python Package Index (PyPI).</p>
            <div className="code-snippet">
              <span className="comment"># Run the following command in your terminal</span><br/>
              pip install m3-mcp
            </div>
          </div>

          <div className="paper-preview" style={{ marginBottom: '40px' }}>
            <h3>2. Installation from Source</h3>
            <p>For the latest development features, you can install m3 directly from the GitHub repository.</p>
            <div className="code-snippet">
              <span className="comment"># 1. Clone the repository</span><br/>
              git clone https://github.com/rafiattrach/m3.git<br/><br/>
              <span className="comment"># 2. Navigate to the project directory</span><br/>
              cd m3<br/><br/>
              <span className="comment"># 3. Install in editable mode</span><br/>
              pip install -e .
            </div>
          </div>

          <div className="paper-preview">
            <h3>Configuration</h3>
            <p>After installation, you'll need to configure m3 to connect to your MIMIC database. Create a configuration file at `~/.m3/config.yml` with your database credentials.</p>
            <div className="code-snippet">
              <span className="comment"># Example config.yml</span><br/>
              <span className="keyword">database:</span><br/>
              <span className="string">  type: "bigquery"</span><br/>
              <span className="string">  project_id: "your-gcp-project-id"</span><br/>
              <span className="string">  dataset: "mimic_iv"</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Installation;
