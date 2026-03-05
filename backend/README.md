# AI Business Setup Assistant (Hindi + Tamil)

Voice-powered business registration assistant that accepts Hindi and Tamil audio input, extracts structured business data, suggests required licenses, and answers regulatory questions using RAG.

**Hackathon demo — not production-grade.**

---

## Tech Stack

| Component | Technology |
|---|---|
| Framework | FastAPI + Uvicorn |
| Speech-to-Text | Sarvam AI (saaras:v3) |
| LLM | Groq (llama-3.1-8b-instant) |
| Vector Store | ChromaDB (all-MiniLM-L6-v2 embeddings) |
| Database | SQLite + SQLAlchemy |
| Languages | Hindi (hi-IN), Tamil (ta-IN) |

---

## Quick Start

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
```

Edit `.env` and add your keys:
```
SARVAM_API_KEY=your_sarvam_key
GROQ_API_KEY=your_groq_key
```

- **Sarvam AI**: Sign up at [console.sarvam.ai](https://console.sarvam.ai)
- **Groq**: Sign up at [console.groq.com](https://console.groq.com)

### 3. Run the server

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Server starts at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

---

## API Endpoints

### `POST /voice-input`
Upload Hindi/Tamil audio → transcribe → extract business data → save profile → suggest licenses.

```bash
curl -X POST http://localhost:8000/voice-input \
  -F "file=@recording.wav"
```

**Response:**
```json
{
  "id": 1,
  "transcript": "मैं चेन्नई में एक रेस्टोरेंट खोलना चाहता हूं...",
  "detected_language": "hi-IN",
  "profile": {
    "business_type": "restaurant",
    "city": "Chennai",
    "seating_capacity": 80,
    "turnover": 5000000,
    "serves_food": true,
    "serves_alcohol": false
  },
  "suggested_licenses": [
    {"license": "Trade License", "reason": "Mandatory for all businesses."},
    {"license": "FSSAI", "reason": "Food service requires FSSAI registration."},
    {"license": "Fire NOC", "reason": "Seating capacity exceeds 50."},
    {"license": "GST Registration", "reason": "Turnover exceeds ₹40 lakhs."}
  ]
}
```

### `GET /profile/{id}`
Retrieve a saved business profile.

```bash
curl http://localhost:8000/profile/1
```

### `GET /suggest-licenses/{id}`
Get license suggestions for a profile.

```bash
curl http://localhost:8000/suggest-licenses/1
```

### `POST /ask`
Ask a regulatory question (RAG-powered from Chennai licensing document).

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "FSSAI लाइसेंस के लिए क्या दस्तावेज चाहिए?", "language": "hi-IN"}'
```

**Response:**
```json
{
  "answer": "FSSAI लाइसेंस के लिए आपको...",
  "language": "hi-IN"
}
```

---

## Demo Flow

1. **User uploads Hindi/Tamil voice recording** → `POST /voice-input`
2. **System transcribes** audio using Sarvam AI STT
3. **Business profile auto-fills** via Groq LLM extraction
4. **License suggestions appear** from rule-based engine
5. **User asks compliance question** → `POST /ask`
6. **RAG answers** from Chennai restaurant licensing document

---

## Project Structure

```
backend/
├── main.py                  # FastAPI app & endpoints
├── database.py              # SQLAlchemy config (SQLite)
├── models/
│   └── profile.py           # ORM model + Pydantic schemas
├── services/
│   ├── speech_service.py    # Sarvam AI STT integration
│   ├── extraction_service.py # Groq LLM structured extraction
│   ├── license_service.py   # Rule-based license suggestions
│   └── rag_service.py       # ChromaDB + Groq RAG pipeline
├── data/
│   └── Chennai Restaurant Licensing... .docx
├── requirements.txt
├── .env.example
└── README.md
```

---

## Constraints

- Only Hindi and Tamil audio supported
- No authentication
- No government API integration
- No web scraping
- Simple rule-based license logic (not LLM)
- RAG limited to uploaded document only
