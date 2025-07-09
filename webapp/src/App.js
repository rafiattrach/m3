import React, { useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import Hero from './components/Hero';
import Contact from './components/Contact';
import Paper from './components/Paper';
import Demos from './components/Demos';
import Explanation from './components/Explanation';
import Features from './components/Features';
import Citation from './components/Citation';
import CTA from './components/CTA';
import Footer from './components/Footer';
import Installation from './components/Installation';

function App() {
  useEffect(() => {
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

  return (
    <div className="App">
      <Header />
      <Hero />
      <Contact />
      <Paper />
      <Demos />
      <Explanation />
      <Features />
      <Installation />
      <Citation />
      <CTA />
      <Footer />
    </div>
  );
}

export default App;
