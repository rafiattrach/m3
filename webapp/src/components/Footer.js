import React from 'react';

const Footer = () => {
  return (
    <footer style={{
      backgroundColor: '#000',
      color: '#fff',
      textAlign: 'center',
      padding: '60px 20px',
      marginTop: 'auto',
      width: '100%',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif'
    }}>
      <p style={{
        fontSize: '18px',
        fontWeight: '300',
        margin: '0 0 30px 0',
        lineHeight: '1.6',
        color: '#e5e5e5',
        fontStyle: 'italic'
      }}>
        "Originated from Open Source, give back to Open Source."
      </p>
      <p style={{
        fontSize: '13px',
        margin: '0 0 8px 0',
        color: '#999',
        fontWeight: '400',
        letterSpacing: '0.5px'
      }}>
        Licensed under MIT License
      </p>
      <p style={{
        fontSize: '13px',
        margin: '0',
        color: '#999',
        fontWeight: '400',
        letterSpacing: '0.5px'
      }}>
        © 2025 MIT Critical Data
      </p>
    </footer>
  );
};

export default Footer;
