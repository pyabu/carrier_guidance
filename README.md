# CareerGuidance.me 🚀

An AI-powered job portal and career guidance platform built for Indian students and professionals. CareerGuidance aggregates jobs from 8+ portals, uses AI to parse resumes, matches candidates to jobs, and provides an interactive AI Career Copilot.

## ✨ Key Features

- **🤖 AI Resume Parsing & Matching**: 
  - Users can upload PDFs/DOCs (handled via `pdfplumber` & `python-docx`).
  - Powered by **OpenRouter API** (Gemma, Llama, Qwen) with a robust fallback to **Google Gemini 2.0**.
  - Extracts skills, experience, and location to dynamically filter and rank matching jobs based on an AI composite score.
- **🌐 Real-Time Job Aggregation**:
  - Auto-scrapes and deduplicates jobs every 12 hours from 8+ sources including Naukri, LinkedIn, Indeed, Foundit, Internshala, TimesJobs, Freshersworld, and Himalayas.
  - Dedicated localized pages for **All India** (`/jobs/india`) and **Tamil Nadu** (`/jobs/tamilnadu`).
- **💬 AI Career Copilot**:
  - An interactive chatbot that provides personalized career advice, roadmap generation, and market trends based on Indian job market data.
- **⚡ Vercel & Supabase Ready**:
  - Designed for serverless deployment on Vercel (handles read-only filesystems using `/tmp`).
  - Stores user data, parsed resumes, and scraped jobs in **Supabase (PostgreSQL)**.

## 🛠️ Tech Stack

- **Backend**: Python 3.9, Flask
- **Frontend**: HTML5, Vanilla CSS3 (custom styling, no Tailwind), JavaScript
- **Database**: Supabase
- **AI/LLMs**: OpenRouter (Primary), Google GenAI / Gemini (Fallback)
- **Scraping**: BeautifulSoup, `fake_useragent`, custom request rotation
- **Deployment**: Vercel Serverless Functions

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- A Supabase account and project
- API keys for OpenRouter and Google Gemini

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/pyabu/carrier_guidance.git
cd carrier_guidance
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory and add the following:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENROUTER_API_KEY=your_openrouter_key
GEMINI_API_KEY=your_gemini_key
```

### 4. Running the App Locally
Start the Flask development server:
```bash
python3 app.py
```
*The app will be available at http://127.0.0.1:5000*

## 📁 Project Structure

```text
├── app.py                      # Main Flask application & API routes
├── requirements.txt            # Python dependencies
├── scraper/                    
│   └── job_scraper.py          # Auto-scraper for 8+ job portals
├── templates/                  # Jinja2 HTML Templates
│   ├── base.html               # Main layout wrapper
│   ├── india_jobs.html         # All-India jobs feed
│   ├── tn_jobs.html            # Tamil Nadu localized jobs feed
│   ├── resume_match_widget.html# Upload & parsing UI component
│   ├── career_guidance.html    # AI Copilot chatbot interface
│   └── resume_builder.html     # Resume building UI
├── static/                     # CSS, JS, and Images
└── data/
    └── trends.json             # Cached market trends used by AI
```

## 🧠 AI Parsing Architecture

The resume parser (`_parse_resume_with_ai` in `app.py`) is designed for high reliability and cost-efficiency:
1. **Primary**: OpenRouter API (`google/gemma-4-31b-it:free`).
2. **Rate-Limit Fallbacks**: Automatically rotates through `meta-llama/llama-3.3-70b-instruct:free`, `qwen/qwen3-next-80b-a3b-instruct:free`, and `liquid/lfm-2.5-1.2b-instruct:free` if 429 Too Many Requests are hit.
3. **Failsafe**: If OpenRouter fails completely, it gracefully falls back to `gemini-2.0-flash` via the `google.genai` SDK.

## 🤝 Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License
This project is proprietary / open-source (modify based on your licensing preference).
