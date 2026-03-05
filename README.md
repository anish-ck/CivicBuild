# CivicBuild — AI Business Setup Assistant

An AI-powered assistant that guides entrepreneurs through setting up a restaurant or food business in India, with support for **Hindi & Tamil voice input**, multi-city licensing RAG, blueprint compliance checking, and auto-email PDF reports.

---

## Features

- **Voice-to-Profile**: Speak your business details in Hindi or Tamil — Sarvam AI transcribes and Groq LLM extracts structured data (city, business type, seating, turnover, alcohol/food flags)
- **Multi-City RAG**: ChromaDB-backed licensing knowledge for Chennai, Mumbai, Bangalore, Delhi, Hyderabad, and Kolkata — city-filtered retrieval via `all-MiniLM-L6-v2`
- **Blueprint Compliance**: Upload a floor plan image → Google Vision OCR → Groq extracts dimensions/exits/kitchen → city-specific compliance check
- **Location Suggestion**: AI-suggested commercial zones for the detected city using Google Maps geocoding
- **PDF Report + Email**: ReportLab generates a compliance advisory PDF, sent via Gmail API (OAuth 2.0)
- **Follow-up Q&A**: Ask city-specific licensing questions via RAG-powered chat

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React Native (Expo SDK 55), TypeScript, expo-router |
| Backend | Python 3.13, FastAPI, SQLAlchemy + SQLite |
| Voice | Sarvam AI (`saaras:v3` STT + `mayura:v1` translate) |
| LLM | Groq (`llama-3.1-8b-instant`) |
| RAG | ChromaDB + `all-MiniLM-L6-v2` (sentence-transformers) |
| Vision | Google Cloud Vision API |
| Maps | Google Maps Geocoding API |
| Email | Gmail API (OAuth 2.0) |
| PDF | ReportLab |

---

## Project Structure

```
CivicBuild/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # API keys & constants
│   ├── database.py              # SQLAlchemy setup
│   ├── models/                  # Pydantic + ORM models
│   ├── routers/                 # API route handlers
│   │   ├── auth.py              # Gmail OAuth
│   │   ├── blueprint.py         # Blueprint upload + compliance
│   │   ├── geolocation.py       # Location suggestion
│   │   └── lifecycle.py         # Full process + PDF + email
│   ├── services/
│   │   ├── rag_service.py       # ChromaDB multi-city RAG
│   │   ├── extraction_service.py# Groq LLM voice extraction
│   │   ├── blueprint_scanner.py # Vision API OCR
│   │   ├── geolocation_service.py# Maps + city-aware prompts
│   │   ├── gmail_service.py     # Gmail OAuth send
│   │   └── pdf_generator.py     # ReportLab PDF
│   └── data/                    # City licensing .docx documents
└── frontend/
    ├── app/index.tsx            # Main chat UI
    └── services/api.ts          # Backend API calls
```

---

## Supported Cities

Chennai · Mumbai · Bangalore · Delhi · Hyderabad · Kolkata

---

## Setup

### Backend
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
# Copy .env.example to .env and fill in API keys
python main.py
```

### Frontend
```bash
cd frontend
npm install
npx expo start
```

### Environment Variables (`.env`)
```
SARVAM_API_KEY=...
GROQ_API_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_MAPS_API_KEY=...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
```

---

## Gmail OAuth Setup
1. Visit `http://localhost:8000/auth/login` in your browser
2. Authorize with your Google account
3. Token is stored — emails will send automatically thereafter

---

*Built for the CivicBuild Hackathon — AI-assisted municipal compliance for Indian entrepreneurs.*
AI Business Setup Assistant — voice-based (Hindi/Tamil), multi-city RAG licensing guidance, blueprint compliance, geolocation, PDF reports &amp; Gmail integration
