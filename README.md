# Insight AI: AI-Powered Risk Intelligence

**Insight AI** is an intelligent platform for monitoring and analyzing risks, developed by Team `libc`. It automatically processes daily media news to extract critical information, separate facts from editorial noise, and calculate potential political, market, and reputational risks for targeted companies in a personalized portfolio.

## Features

- **Automated Media Parsing:** Replaces manual news reading with automated agent-assisted parsing using advanced LLMs (Google Gemini & Anthropic Claude Haiku).
- **Signal vs. Noise Separation:** AI models act as a filter to eliminate irrelevant media noise, accurately distinguishing between editorial opinions and factual reporting.
- **Risk Radar Pipeline:** Proactively identifies contextual deviations, such as legislative changes or reputational events that could affect an entity, categorizing them by scale and relevance.
- **Custom Portfolios:** Real-time tracking of companies through a responsive web dashboard.
- **Secure & Scalable:** Async backend integrated with Supabase authentication, fully containerized for simplified deployment.

## Tech Stack

**Backend**

- Python 3
- FastAPI (Asynchronous REST API)
- Supabase (Authentication & Database storage)
- LLMs Integration (Anthropic Haiku, Google Gemini via OpenRouter or native APIs)

**Frontend**

- React + Vite
- TypeScript
- Tailwind CSS
- React Router

**Infrastructure**

- Docker & Docker Compose

## AI Analytical Pipeline (The 3 Pillars)

The analytical flow is separated into three distinct steps:

1. **Continuous Collection:** Aggregation of news streams for companies in user portfolios.
2. **AI Analysis (LLMs):** Fast API classification based on three main pillars:
   - Fact / Opinion Inference
   - Signal / Noise Classification
   - Risk Radar (Political & Reputational Impact Assessment)
3. **Dashboard UI:** Rendering aggregated impact scores and alerts onto a sleek web interface.

## Prerequisites

- Docker and Docker Compose (recommended for easy startup)
- Node.js 18+ (for local frontend development)
- Python 3.10+ (for local backend development)
- API Keys for Google Gemini / Anthropic (or OpenRouter)
- Supabase Account credentials

## Getting Started


1. Clone the repository and navigate to the root directory.
2. Ensure you have your `.env` files set up in `backend/` (see Environment Variables below).
3. Build and start the containers:
   ```bash
   docker-compose up --build
   ```
4. The frontend will be accessible at `http://localhost:5173` (or the port mapped in your compose file).
5. The backend API documentation will be accessible at `http://localhost:8000/docs`.


## Environment Variables

You must set up the appropriate environment variables before running the application. Create `.env` files in both the frontend and backend directories.

**Backend (`backend/.env`):**

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_service_role_key
GEMINI_API_KEY=your_google_gemini_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

