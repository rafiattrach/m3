import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const Header = () => {
  const [stars, setStars] = useState(4);

  useEffect(() => {
    fetch('https://api.github.com/repos/MIT-LCP/m3')
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

  return (
    <header>
      <nav className="container">
        <div className="logo"><Link to="/">m3</Link></div>
        <ul className="nav-links">
          <li><a href="/#demos">Demos</a></li>
          <li><a href="/#paper">Paper</a></li>
          <li><Link to="/installation">Installation</Link></li>
          <li><Link to="/documentation">Documentation</Link></li>
        </ul>
        <div>
          <a href="https://github.com/MIT-LCP/m3" target="_blank" rel="noopener noreferrer" className="btn-github">
            <span>{stars.toLocaleString()} ⭐</span> Star on GitHub
          </a>
        </div>
      </nav>
    </header>
  );
};

export default Header;
