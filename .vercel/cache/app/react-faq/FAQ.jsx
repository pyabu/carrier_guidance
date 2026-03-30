import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import "./FAQ.css";

const faqData = [
  {
    question: "What is Careerguidance?",
    answer:
      "Careerguidance is India's all-in-one career guidance and job portal that helps Indian students, freshers, and professionals. We provide job listings from top Indian & global companies (scraped daily), career roadmaps for B.Tech/MCA/BCA graduates, resume building tools tailored for the Indian market, campus placement preparation guides, and AI-powered career recommendations — all completely free.",
  },
  {
    question: "Is Careerguidance free to use?",
    answer:
      "Yes! All core features including job browsing, career guidance, resume builder, and career roadmaps are completely free for Indian students and professionals. We believe every Indian engineering student deserves quality career guidance regardless of their college tier. We plan to offer premium features like AI resume analysis and advanced analytics in the future.",
  },
  {
    question: "How often are job listings updated?",
    answer:
      "Our AI-powered job scraper runs every 24 hours, pulling fresh job listings from multiple sources including Indian company career pages (TCS, Infosys, Flipkart, Razorpay, etc.), global job boards, LinkedIn, and API feeds. Jobs are available across 14+ Indian cities including Bangalore, Mumbai, Delhi NCR, Hyderabad, Pune, Chennai, and more. This ensures you always see the latest opportunities in the Indian job market.",
  },
  {
    question: "How do I apply for a job?",
    answer:
      'When you find a job you\'re interested in, click the "Apply Now" button on the job card or detail page. This will redirect you to the company\'s official application page where you can submit your application directly. We recommend using our Resume Builder to create an ATS-friendly resume first!',
  },
  {
    question: "What career roadmaps are available?",
    answer:
      "We offer detailed career roadmaps for: AI/Machine Learning, Full Stack Web Development, Data Science & Analytics, Cloud & DevOps, Mobile App Development, and Cybersecurity. Each roadmap includes step-by-step learning paths with Indian platforms like NPTEL, GeeksforGeeks, CodeChef & Internshala, recommended resources, tips for campus placements, and related job opportunities in India.",
  },
  {
    question: "How does the AI Career Suggestion feature work?",
    answer:
      "Our AI analyzes your skills, interests, and current market trends to provide personalized career recommendations. It matches your profile against thousands of job roles to show you career paths with the highest compatibility scores.",
  },
  {
    question: "Is my data safe and private?",
    answer:
      "Yes, we take data privacy seriously. Your personal information is encrypted and never shared with third parties without your consent.",
    hasPrivacyLink: true,
  },
  {
    question: "How can I contact support?",
    answer:
      "You can reach us through our Contact page, email us at support@careerguidance.com, or call us at +91 98765 43210. We respond to all inquiries within 24 hours during business hours (Mon-Fri, 9AM-6PM IST).",
    hasContactLink: true,
  },
];

function FAQItem({ faq, index, activeIndex, onToggle }) {
  const isActive = activeIndex === index;

  return (
    <div className={`faq-item ${isActive ? "active" : ""}`} data-aos="fade-up">
      <button className="faq-question" onClick={() => onToggle(index)}>
        {faq.question}
        <i className="fas fa-chevron-down" />
      </button>
      <div className="faq-answer">
        <p>
          {faq.hasPrivacyLink ? (
            <>
              {faq.answer} You can read our full{" "}
              <Link to="/privacy">Privacy Policy</Link> for detailed
              information about how we handle your data.
            </>
          ) : faq.hasContactLink ? (
            <>
              You can reach us through our{" "}
              <Link to="/contact">Contact page</Link>, email us at
              support@careerguidance.com, or call us at +91 98765 43210. We
              respond to all inquiries within 24 hours during business hours
              (Mon-Fri, 9AM-6PM IST).
            </>
          ) : (
            faq.answer
          )}
        </p>
      </div>
    </div>
  );
}

export default function FAQ() {
  const [activeIndex, setActiveIndex] = useState(null);

  // Initialize AOS if available
  useEffect(() => {
    if (window.AOS) {
      window.AOS.refresh();
    }
  }, []);

  const handleToggle = (index) => {
    setActiveIndex((prev) => (prev === index ? null : index));
  };

  return (
    <>
      {/* Page Header */}
      <div className="page-header">
        <div className="container">
          <div className="breadcrumb">
            <Link to="/">Home</Link>{" "}
            <i className="fas fa-chevron-right" /> FAQ
          </div>
          <h1>❓ Frequently Asked Questions</h1>
          <p>
            Find answers to the most common questions about Careerguidance
          </p>
        </div>
      </div>

      {/* FAQ List */}
      <section>
        <div className="container">
          <div className="faq-list">
            {faqData.map((faq, index) => (
              <FAQItem
                key={index}
                faq={faq}
                index={index}
                activeIndex={activeIndex}
                onToggle={handleToggle}
              />
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="container" data-aos="fade-up">
          <h2>Still have questions?</h2>
          <p>Our support team is always here to help you.</p>
          <Link to="/contact" className="btn btn-white btn-lg">
            <i className="fas fa-envelope" /> Contact Support
          </Link>
        </div>
      </section>
    </>
  );
}
