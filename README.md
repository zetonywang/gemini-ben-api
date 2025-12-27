# Gemini + BEN Bridge Analysis API

This API provides bridge hand analysis using:
- **Gemini** - Google's AI for natural language analysis
- **BEN** - Bridge Engine for computational analysis
- **Combined** - Gemini enhanced with BEN's insights

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/api/analyze/gemini` | POST | Gemini-only analysis |
| `/api/analyze/ben` | POST | BEN-only analysis |
| `/api/analyze/combined` | POST | Gemini + BEN together |
| `/api/analyze/compare` | POST | Compare all three |

## Request Format

```json
{
    "dealer": "S",
    "vuln": [true, true],
    "hands": [
        "AJ87632.J96.753.",
        "K9.Q8542.T6.AJ74",
        "QT4.A.KJ94.KQ986",
        "5.KT73.AQ82.T532"
    ],
    "auction": ["1N", "PASS", "4H", "PASS", "4S", "PASS", "PASS", "PASS"],
    "play": ["C2", "D3", "CA", "C6"]
}
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `BEN_API_URL` | URL to your BEN API (e.g., ngrok URL) |

## Local Development

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"
export BEN_API_URL="https://your-ngrok-url.ngrok-free.dev"
python app.py
```

## Deploy to Railway

1. Push this repo to GitHub
2. Create new project on Railway
3. Connect your GitHub repo
4. Add environment variables
5. Deploy!
