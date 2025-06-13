import React, { useState, useEffect } from 'react';

const Header = () => {
  const [stars, setStars] = useState(3);

  useEffect(() => {
    fetch('https://api.github.com/repos/rafiattrach/m3')
      .then(response => {
        if (!response.ok) {
          return;
        }
        return response.json();
      })
      .then(data => {
        if (data && data.stargazers_count !== undefined) {
          setStars(data.stargazers_count);
        }
      })
      .catch(error => {
        console.error('Error fetching GitHub stars:', error);
      });
  }, []);

  const scrollToSection = (sectionId) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <header>
      <nav className="container">
        <div className="logo">
          <button
            onClick={scrollToTop}
            style={{
              background: 'none',
              border: 'none',
              color: '#0052ff',
              fontSize: '28px',
              fontWeight: '600',
              letterSpacing: '-0.5px',
              fontFamily: "'Courier New', monospace",
              cursor: 'pointer',
              textDecoration: 'none',
              padding: 0
            }}
          >
            m3
          </button>
        </div>
        <ul className="nav-links">
          <li><button onClick={() => scrollToSection('paper')}>Paper</button></li>
          <li><button onClick={() => scrollToSection('demos')}>Demos</button></li>
          <li><button onClick={() => scrollToSection('installation')}>Installation</button></li>
        </ul>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <a
            href="https://pypi.org/project/m3-mcp/"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              padding: '10px',
              textDecoration: 'none',
              color: 'inherit',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              fontWeight: 'bold'
            }}
          >
            <span className="star-count">📦 PyPI</span>
          </a>
          <a href="https://github.com/rafiattrach/m3" target="_blank" rel="noopener noreferrer" className="btn-github">
            <span className="star-count">{stars.toLocaleString()} ⭐</span> Star on GitHub
          </a>

        </div>
      </nav>
    </header>
  );
};

export default Header;
