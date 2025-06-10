import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

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
    // If we're not on the main page, navigate to it first
    if (window.location.hash !== '#/') {
      window.location.hash = '#/';
      // Wait a moment for navigation to complete, then scroll
      setTimeout(() => {
        const element = document.getElementById(sectionId);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    } else {
      // We're already on the main page, just scroll
      const element = document.getElementById(sectionId);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  };

  return (
    <header>
      <nav className="container">
        <div className="logo"><Link to="/">m3</Link></div>
        <ul className="nav-links">
          <li><button onClick={() => scrollToSection('demos')}>Demos</button></li>
          <li><button onClick={() => scrollToSection('paper')}>Paper</button></li>
          <li><Link to="/installation">Installation</Link></li>
          <li><Link to="/documentation">Documentation</Link></li>
        </ul>
        <div>
          <a href="https://github.com/rafiattrach/m3" target="_blank" rel="noopener noreferrer" className="btn-github">
            <span className="star-count">{stars.toLocaleString()} ⭐</span> Star on GitHub
          </a>
        </div>
      </nav>
    </header>
  );
};

export default Header;
