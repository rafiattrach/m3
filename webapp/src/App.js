import React, { useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import './App.css';
import Header from './components/Header';
import Hero from './components/Hero';
import Paper from './components/Paper';
import Demos from './components/Demos';
import Explanation from './components/Explanation';
import Features from './components/Features';
import CTA from './components/CTA';
import Footer from './components/Footer';
import Documentation from './components/Documentation';
import Installation from './components/Installation';

function App() {
  useEffect(() => {
    // Smooth scrolling for anchor links
    const smoothScroll = (targetId) => {
      const target = document.querySelector(targetId);
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    };

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const targetId = this.getAttribute('href');
        // If on a different page, navigate first then scroll
        if (window.location.pathname !== '/') {
          window.location.href = `/${targetId}`;
        } else {
          smoothScroll(targetId);
        }
      });
    });

    // Header scroll effect
    const handleScroll = () => {
      const header = document.querySelector('header');
      if (header) {
        if (window.scrollY > 100) {
          header.style.background = 'rgba(255, 255, 255, 0.98)';
          header.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
        } else {
          header.style.background = 'rgba(255, 255, 255, 0.95)';
          header.style.boxShadow = 'none';
        }
      }

      const scrolled = window.pageYOffset;
      const laptopMockup = document.querySelector('.laptop-mockup');

      if (laptopMockup) {
          const rate = scrolled * 0.2;
          laptopMockup.style.transform = `translateY(${rate}px)`;
      }

      const ctaSection = document.querySelector('.cta-section');
      if (ctaSection) {
          const rate = scrolled * 0.1;
          ctaSection.style.backgroundPosition = `center ${rate}px`;
      }
    };

    window.addEventListener('scroll', handleScroll);

    // Intersection Observer for animations
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, observerOptions);

    document.querySelectorAll('.fade-in').forEach(el => {
      observer.observe(el);
    });

    // Add interactive hover effects for demo cards
    document.querySelectorAll('.demo-card').forEach(card => {
      card.addEventListener('mouseenter', () => {
          card.style.transform = 'translateY(-8px) scale(1.02)';
      });

      card.addEventListener('mouseleave', () => {
          card.style.transform = 'translateY(0) scale(1)';
      });
    });

    // Animate dashboard cards on scroll
    const animateDashboard = () => {
        const cards = document.querySelectorAll('.dashboard-card');
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.style.transform = 'translateY(0)';
                card.style.opacity = '1';
            }, index * 200);
        });
    };

    // Initialize dashboard animation
    setTimeout(animateDashboard, 1000);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      // Clean up other event listeners if necessary
    };
  }, []);

  const MainPage = () => (
    <>
      <Hero />
      <Paper />
      <Demos />
      <Explanation />
      <Features />
      <CTA />
    </>
  );

  return (
    <Router>
      <div className="App">
        <Header />
        <Routes>
          <Route path="/" element={<MainPage />} />
          <Route path="/documentation" element={<Documentation />} />
          <Route path="/installation" element={<Installation />} />
        </Routes>
        <Footer />
      </div>
    </Router>
  );
}

export default App;
