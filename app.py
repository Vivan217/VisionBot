import time

import streamlit as st
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from prompts import SYSTEM_PROMPT, USER_PROMPT
from whatsapp import send_whatsapp, write_summary

MODEL = "gemini-3.8-flash"  # main model
FALLBACK_MODELS = []  # used if the main one is overloaded (503)


class FoodItem(BaseModel):
    name: str
    portion: str
    calories: int
    protein_g: float


class MealAnalysis(BaseModel):
    is_food: bool
    items: list[FoodItem]
    total_calories: int
    total_protein_g: float
    note: str


@st.cache_resource
def get_client() -> genai.Client:
    """Built once and reused on every rerun and by every part of the app."""
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


def generate_with_retry(contents, config=None):
    """Retries on 503/overload. Skips a model that is no longer available (404)."""
    client = get_client()
    last_error = None
    for model in [MODEL, *FALLBACK_MODELS]:
        for attempt in range(4):
            try:
                return client.models.generate_content(model=model, contents=contents, config=config)
            except errors.ServerError as e:  # 5xx: overloaded, wait and retry
                last_error = e
                time.sleep(2 ** (attempt + 1))  # 2s, 4s, 8s, 16s
            except errors.ClientError as e:
                if e.code == 404:  # model not available, try the next one
                    last_error = e
                    break
                raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("Failed to generate content: all models and retries exhausted.")


def analyze_meal(image_bytes: bytes, mime_type: str) -> MealAnalysis:
    response = generate_with_retry(
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            USER_PROMPT,
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=MealAnalysis,
        ),
    )
    return response.parsed


st.set_page_config(page_title="VisionBot", page_icon="🍽️", layout="centered")

st.markdown(
    """
<style>
.block-container {max-width: 760px; padding-top: 2rem;}
.hero {padding: 1.4rem 1.6rem; border-radius: 18px; margin-bottom: 1.2rem;
       background: linear-gradient(135deg, #ff7a18 0%, #af002d 100%); color: #fff;}
.hero h1 {margin: 0; font-size: 2rem; color: #fff;}
.hero p {margin: .3rem 0 0; opacity: .92;}
div[data-testid="stMetric"] {background: rgba(128,128,128,.10); border-radius: 14px; padding: .8rem 1rem;}
</style>
<div class="hero"><h1>🍽️ VisionBot</h1><p>Snap your meal. Get calories and protein in seconds.</p></div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ Settings")
    protein_goal = st.number_input("Daily protein goal (g)", min_value=20, max_value=300, value=100, step=5)
    st.caption("Values are estimates from a photo, not medical or dietary advice.")

tab_upload, tab_camera = st.tabs(["📁 Upload", "📷 Camera"])
with tab_upload:
    uploaded = st.file_uploader(
        "Upload a photo of your meal", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed"
    )
with tab_camera:
    shot = st.camera_input("Take a photo of your meal", label_visibility="collapsed")
image = shot or uploaded

if image:
    st.image(image, width="stretch")
    if st.button("🔍 Analyze meal", type="primary", width="stretch"):
        try:
            with st.spinner("Looking at your food..."):
                result = analyze_meal(image.getvalue(), image.type)
            # Keep the result in session_state so it survives the next button click
            st.session_state["result"] = result
            st.session_state["result_file"] = image.file_id
            st.session_state.pop("summary", None)
        except errors.ServerError:
            st.error("Gemini is overloaded right now. Wait a minute and press Analyze again.")

# Show the result only if it belongs to the image currently selected
result = st.session_state.get("result")
if image and result and st.session_state.get("result_file") == image.file_id:
    if result.is_food:
        c1, c2 = st.columns(2)
        c1.metric("🔥 Calories", f"{result.total_calories} kcal")
        c2.metric("💪 Protein", f"{result.total_protein_g:.1f} g")

        share = min(result.total_protein_g / protein_goal, 1.0)
        st.progress(share, text=f"{share * 100:.0f}% of your {protein_goal} g daily protein goal")

        st.subheader("What's on the plate")
        for item in result.items:
            with st.container(border=True):
                name_col, kcal_col, protein_col = st.columns([3, 1, 1])
                name_col.markdown(f"**{item.name}**")
                name_col.caption(item.portion)
                kcal_col.markdown(f"**{item.calories}** kcal")
                protein_col.markdown(f"**{item.protein_g:.1f}** g protein")
        st.caption(f"ℹ️ {result.note}")

        with st.expander("📲 Send recap to WhatsApp"):
            number = st.text_input("Your WhatsApp number (with country code)", placeholder="+91XXXXXXXXXX")
            if st.button("Send to WhatsApp", type="primary"):
                if not number.startswith("+"):
                    st.error("Start the number with + and the country code, like +91...")
                else:
                    try:
                        with st.spinner("Writing and sending..."):
                            summary = write_summary(generate_with_retry, result)
                            sid = send_whatsapp(number, summary)
                        st.session_state["summary"] = summary
                        st.success(f"Sent! (Twilio message id: {sid})")
                    except Exception as e:
                        st.error(f"Couldn't send: {e}")
            if "summary" in st.session_state:
                st.text(st.session_state["summary"])
    else:
        st.warning("I couldn't spot any food in that photo. Try another one!")