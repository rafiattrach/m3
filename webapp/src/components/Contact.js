import React, { useState } from 'react';
import emailjs from '@emailjs/browser';

const Contact = () => {
  // EmailJS configuration with your actual credentials
  const EMAILJS_CONFIG = {
    serviceId: 'm3_contact_service',
    templateId: 'template_sn5rm19',
    publicKey: 'aUrTfsE6oJtpIe1ac'
  };

  const [contactForm, setContactForm] = useState({
    email: '',
    inquiryType: 'hospital',
    message: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setContactForm(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus(null);

    try {
      // Prepare template parameters
      const templateParams = {
        user_email: contactForm.email,
        user_name: contactForm.email.split('@')[0], // Extract name from email
        inquiry_type: contactForm.inquiryType,
        message: contactForm.message || 'No additional message provided',
        inquiry_type_label: contactForm.inquiryType === 'hospital' ? 'Hospital/EHR MCP Request' :
                           contactForm.inquiryType === 'suggestions' ? 'Suggestions & Feedback' : 'General Contact',
        timestamp: new Date().toLocaleString()
      };

      // Send email using EmailJS
      const response = await emailjs.send(
        EMAILJS_CONFIG.serviceId,
        EMAILJS_CONFIG.templateId,
        templateParams,
        EMAILJS_CONFIG.publicKey
      );

      console.log('Email sent successfully:', response);
      setSubmitStatus({ type: 'success', message: 'Message sent successfully! We\'ll get back to you soon.' });
      setContactForm({ email: '', inquiryType: 'hospital', message: '' });

    } catch (error) {
      console.error('Error sending email:', error);
      setSubmitStatus('error');
      // Store the specific error message for display
      setSubmitStatus({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getErrorMessage = (error) => {
    // Handle different types of errors
    if (error.message?.includes('rate limit') || error.status === 429) {
      return 'Too many emails sent recently. Please try again in a few minutes.';
    }
    if (error.message?.includes('invalid email') || error.status === 400) {
      return 'Please check your email address and try again.';
    }
    if (error.message?.includes('network') || !navigator.onLine) {
      return 'Network error. Please check your internet connection and try again.';
    }
    if (error.status === 403) {
      return 'Service temporarily unavailable. Please try again later.';
    }
    return 'Failed to send message. Please try again later.';
  };

  return (
    <>
      <style>
        {`
          .contact-section {
            padding: 60px 0;
            background: linear-gradient(135deg, #fbfcfd 0%, #f1f5f9 100%);
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
          }

          .contact-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 0 24px;
          }

          .contact-header {
            text-align: center;
            margin-bottom: 40px;
          }

          .contact-header h2 {
            font-size: 32px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 12px;
          }

          .contact-header p {
            font-size: 18px;
            color: #64748b;
            max-width: 600px;
            margin: 0 auto;
            line-height: 1.6;
          }

          .contact-form {
            background: white;
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(0, 0, 0, 0.05);
          }

          .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
          }

          .form-group {
            display: flex;
            flex-direction: column;
          }

          .form-label {
            font-weight: 500;
            color: #1a1a1a;
            margin-bottom: 8px;
            font-size: 14px;
          }

          .form-input, .form-select, .form-textarea {
            padding: 12px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
            font-family: inherit;
            transition: all 0.3s ease;
            background: white;
          }

          .form-input:focus, .form-select:focus, .form-textarea:focus {
            outline: none;
            border-color: #0052ff;
            box-shadow: 0 0 0 3px rgba(0, 82, 255, 0.1);
          }

          .form-textarea {
            min-height: 80px;
            resize: vertical;
            grid-column: 1 / -1;
          }

          .btn-contact {
            background: #0052ff;
            color: white;
            padding: 12px 32px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
          }

          .btn-contact:hover {
            background: #0041cc;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 82, 255, 0.3);
          }

          .btn-contact:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
          }

          .form-actions {
            display: flex;
            justify-content: center;
            margin-top: 24px;
          }

          .status-message {
            margin-top: 16px;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            text-align: center;
          }

          .status-success {
            background: #dcfce7;
            border: 1px solid #bbf7d0;
            color: #166534;
          }

          .status-error {
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #dc2626;
          }

          @media (max-width: 768px) {
            .contact-section {
              padding: 40px 0;
            }

            .contact-header h2 {
              font-size: 28px;
            }

            .contact-form {
              padding: 24px;
            }

            .form-row {
              grid-template-columns: 1fr;
              gap: 16px;
            }
          }
        `}
      </style>
      <section className="contact-section">
        <div className="contact-container">
          <div className="contact-header fade-in">
            <h2>Let's Connect</h2>
            <p>Need an MCP for your hospital or EHR? Have suggestions? Want to collaborate? We'd love to hear from you!</p>
            <p style={{ fontSize: '16px', color: '#0052ff', fontWeight: '500', marginTop: '8px' }}>
              ⚡ Our team responds within 24 hours
            </p>
          </div>

          <form className="contact-form fade-in" onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label" htmlFor="email">Email Address</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  className="form-input"
                  placeholder="your.email@example.com"
                  value={contactForm.email}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="inquiryType">How can we help?</label>
                <select
                  id="inquiryType"
                  name="inquiryType"
                  className="form-select"
                  value={contactForm.inquiryType}
                  onChange={handleInputChange}
                >
                  <option value="hospital">🏥 Hospital/EHR MCP Request</option>
                  <option value="suggestions">💡 Suggestions & Feedback</option>
                  <option value="general">📧 General Contact</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="message">Message (Optional)</label>
              <textarea
                id="message"
                name="message"
                className="form-textarea"
                placeholder="Tell us more about your needs or suggestions..."
                value={contactForm.message}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-actions">
              <button
                type="submit"
                className="btn-contact"
                disabled={isSubmitting || !contactForm.email}
              >
                {isSubmitting ? (
                  <>
                    <span>⏳</span> Sending...
                  </>
                ) : (
                  <>
                    <span>📮</span> Send Message
                  </>
                )}
              </button>
            </div>

            {submitStatus?.type === 'success' && (
              <div className="status-message status-success">
                ✅ {submitStatus.message}
              </div>
            )}

            {submitStatus?.type === 'error' && (
              <div className="status-message status-error">
                ❌ {submitStatus.message}
              </div>
            )}
          </form>
        </div>
      </section>
    </>
  );
};

export default Contact;
