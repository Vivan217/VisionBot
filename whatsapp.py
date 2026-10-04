import json

import streamlit as st
from twilio.rest import Client

from prompts import WHATSAPP_SUMMARY_PROMPT


@st.cache_resource
def get_twilio() -> Client:
    """Built once, like the Gemini client."""
    return Client(st.secrets["TWILIO_ACCOUNT_SID"], st.secrets["TWILIO_AUTH_TOKEN"])


def write_summary(generate, result, user_text: str = "") -> str:
    """Builds the WhatsApp recap locally, with no extra Gemini call."""
    lines = [f"🍽️ *{result.total_calories} kcal | {result.total_protein_g:.1f}g protein*", ""]
    for i in result.items:
        lines.append(f"• {i.name} ({i.portion}) - {i.calories} kcal, {i.protein_g:.1f}g protein")
    lines += ["", result.note]
    return "\n".join(lines)

def send_whatsapp(to_number: str, text: str) -> str:
    """Sends the recap. Uses the Content Template if a Content SID is set, else a plain body."""
    to = f"whatsapp:{to_number.strip()}"
    from_ = st.secrets["TWILIO_WHATSAPP_FROM"]
    content_sid = st.secrets.get("TWILIO_CONTENT_SID")

    if content_sid:
        # Template variables can't contain newlines, so flatten the recap into one line.
        flat = " | ".join(line.strip() for line in text.splitlines() if line.strip())
        msg = get_twilio().messages.create(
            from_=from_,
            to=to,
            content_sid=content_sid,
            content_variables=json.dumps({"1": flat}),
        )
    else:
        msg = get_twilio().messages.create(from_=from_, to=to, body=text)
    return msg.sid