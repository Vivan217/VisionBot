import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel

from prompts import SYSTEM_PROMPT, USER_PROMPT
from whatsapp import send_whatsapp, write_summary

MODEL = "gemini-3.8-flash"  # same model name you already had working


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


def analyze_meal(image_bytes: bytes, mime_type: str) -> MealAnalysis:
    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            USER_PROMPT,
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=MealAnalysis,
            temperature=0.2,
        ),
    )
    return response.parsed


st.set_page_config(page_title="VisionBot", page_icon="🍽️")
st.title("🍽️ VisionBot: Food & Calorie Scanner")

uploaded = st.file_uploader("Upload a photo of your meal", type=["jpg", "jpeg", "png", "webp"])

if uploaded:
    st.image(uploaded, use_container_width=True)
    if st.button("Analyze"):
        with st.spinner("Looking at your food..."):
            result = analyze_meal(uploaded.getvalue(), uploaded.type)
        # Keep the result in session_state so it survives the next button click
        st.session_state["result"] = result
        st.session_state["result_file"] = uploaded.file_id
        st.session_state.pop("summary", None)

# Show the result only if it belongs to the file currently uploaded
result = st.session_state.get("result")
if uploaded and result and st.session_state.get("result_file") == uploaded.file_id:
    if result.is_food:
        c1, c2 = st.columns(2)
        c1.metric("Calories", f"{result.total_calories} kcal")
        c2.metric("Protein", f"{result.total_protein_g} g")
        st.dataframe(
            [i.model_dump() for i in result.items],
            column_config={"protein_g": st.column_config.NumberColumn("protein (g)", format="%.1f")},
            hide_index=True,
        )
        st.caption(result.note)

        st.divider()
        st.subheader("📲 Send recap to WhatsApp")
        number = st.text_input("Your WhatsApp number (with country code)", placeholder="+91XXXXXXXXXX")
        if st.button("Send to WhatsApp"):
            if not number.startswith("+"):
                st.error("Start the number with + and the country code, like +91...")
            else:
                try:
                    with st.spinner("Writing and sending..."):
                        summary = write_summary(get_client(), MODEL, result)
                        sid = send_whatsapp(number, summary)
                    st.session_state["summary"] = summary
                    st.success(f"Sent! (Twilio message id: {sid})")
                except Exception as e:
                    st.error(f"Couldn't send: {e}")
        if "summary" in st.session_state:
            st.text(st.session_state["summary"])
    else:
        st.warning("I couldn't spot any food in that photo. Try another one!")