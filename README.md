# 🍽️ VisionBot: AI Food & Calorie Scanner

Upload a photo of your meal and VisionBot tells you what's on the plate, with an estimated calorie and protein breakdown. It can also send a short recap straight to your WhatsApp.

Built with **Gemini (vision)**, **Streamlit** and **Twilio WhatsApp**.

## Features

- 📸 **Meal photo analysis**: identifies each food item, estimates portion size, calories and protein
- 🧾 **Structured output**: Gemini returns JSON that matches a fixed schema, so there's no fragile text parsing
- 🚫 **Stays on topic**: non-food photos and off-topic requests get a friendly redirect
- 🇮🇳 **Indian-food aware**: assumes typical Indian home and restaurant portions (dal, rice, roti, etc.)
- 💬 **WhatsApp recap**: a second Gemini call turns the analysis into a short, friendly chat message sent via Twilio
- 🔁 **Resilient**: automatic retries and a fallback model when Gemini is overloaded (503)

## How it works

```
Photo → Streamlit → Gemini (vision) → JSON → Gemini (recap) → Twilio → WhatsApp
```

1. You upload a meal photo in the Streamlit app.
2. The image and a system prompt go to Gemini, which returns a `MealAnalysis` object (items, calories, protein, totals, note).
3. The result is shown on screen as metrics and a table.
4. If you choose to send a recap, a second Gemini call writes a short WhatsApp-style summary from that data.
5. Twilio delivers the message to your WhatsApp number.

## Project structure

```
VisionBot/
├── app.py               # Streamlit UI, Gemini client, analysis + retry logic
├── prompts.py           # System prompt, welcome message, WhatsApp summary prompt
├── whatsapp.py          # Twilio client, recap writer, message sender
├── requirements.txt
└── .streamlit/
    └── secrets.toml.example   # copy to secrets.toml and add your keys
```

## Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/YOUR-USERNAME/VisionBot.git
cd VisionBot
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your keys

Copy the example file and fill in your own values:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

```toml
GEMINI_API_KEY = "your-gemini-key"
TWILIO_ACCOUNT_SID = "AC..."
TWILIO_AUTH_TOKEN = "your-token"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
```

- Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/).
- Get your Account SID and Auth Token from the [Twilio Console](https://console.twilio.com/).
- `.streamlit/secrets.toml` is git-ignored. **Never commit real keys.**

### 3. Join the Twilio WhatsApp Sandbox

1. In the Twilio Console, open **Messaging → Try it out → Send a WhatsApp message**.
2. From your WhatsApp, send `join <your-sandbox-code>` to the sandbox number.
3. Wait for the "You are all set!" reply.

The sandbox only delivers messages to numbers that have joined it, and the join expires after a few days, so rejoin if messages stop arriving.

### 4. Run

```bash
streamlit run app.py
```

Open `http://localhost:8501`, upload a meal photo, click **Analyze**, then enter your number (with country code, e.g. `+91XXXXXXXXXX`) and click **Send to WhatsApp**.

## Configuration

| Setting | Where | Notes |
|---|---|---|
| `MODEL` | `app.py` | Main Gemini model |
| `FALLBACK_MODELS` | `app.py` | Used if the main model keeps returning 503 |
| `temperature` | `app.py` | Set low (0.2) so calorie estimates stay consistent |
| `TWILIO_CONTENT_SID` | `secrets.toml` (optional) | Content Template SID. If omitted, a plain text message is sent |

## Limitations

- Calorie and protein values are **estimates** from a photo, not medical or dietary advice.
- Currently one-way: you upload in the web app and the recap is sent to WhatsApp. Sending photos *to* the bot on WhatsApp is not implemented yet.
- The Twilio sandbox is for testing. A public WhatsApp bot needs a verified WhatsApp Business sender.

## Roadmap

- [ ] Two-way WhatsApp bot (webhook), so users can send photos directly in the chat
- [ ] Daily calorie and protein totals with a protein goal
- [ ] Hindi and Hinglish replies
- [ ] Deploy on Streamlit Community Cloud

## Tech stack

Python · Streamlit · Google Gemini (`google-genai`) · Pydantic · Twilio
