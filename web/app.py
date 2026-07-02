from __future__ import annotations
import os
import sys
import tempfile

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.orchestrator import FieldWiseOrchestrator  # noqa: E402

st.set_page_config(page_title="FieldWise", page_icon="🌱", layout="centered")

LLM_MODE = os.environ.get("FIELDWISE_LLM_MODE", "mock")


@st.cache_resource
def get_orchestrator() -> FieldWiseOrchestrator:
    return FieldWiseOrchestrator()


def render_header() -> None:
    st.title("🌱 FieldWise")
    st.caption("A multi-agent crop health advisor for smallholder farmers.")
    if LLM_MODE == "mock":
        st.info(
            "Running in **MOCK mode** — no live AI model is being called, so this "
            "demo runs free and offline. Diagnoses shown are deterministic mock "
            "data for demonstration. Set `FIELDWISE_LLM_MODE=gemini` with a "
            "`GEMINI_API_KEY` to enable real AI-powered diagnosis.",
            icon="🧪",
        )


def render_input_form():
    with st.form("case_form"):
        st.subheader("Describe what you're seeing")
        description = st.text_area(
            "What does the crop look like? Describe symptoms in your own words.",
            placeholder="e.g. Leaves have brown spots with yellow rings, starting from the bottom of the plant.",
            height=110,
        )
        photo = st.file_uploader("Optional: upload a photo of the affected crop", type=["jpg", "jpeg", "png"])
        col1, col2 = st.columns(2)
        with col1:
            farmer_id = st.text_input("Farmer / Field ID", value="demo_farmer_001",
                                       help="Use a pseudonymous ID, not a real name or phone number.")
        with col2:
            region = st.text_input("Region", value="vijayawada")
        submitted = st.form_submit_button("Get advice", use_container_width=True)
    return submitted, description, photo, farmer_id, region


def render_trace(trace: list[str]) -> None:
    with st.expander("🔍 See how the agents reached this result"):
        for line in trace:
            st.text(line)


def render_report(report) -> None:
    if report.escalated:
        st.warning(
            "**FieldWise isn't confident enough to give automated advice on this case.**\n\n"
            "This has been flagged for review by a human agricultural expert instead of "
            "guessing — that's a deliberate safety choice, not a bug.",
            icon="⚠️",
        )
        render_trace(report.trace)
        return

    st.success(f"**Likely diagnosis:** {report.diagnosis}")
    st.write(report.explanation)

    if report.treatment_options:
        st.subheader("🛒 Locally available treatment")
        for opt in report.treatment_options:
            st.markdown(
                f"- **{opt['product']}** — {opt['approx_price']}  \n"
                f"  via *{opt['supplier_name']}* ({opt['distance_km']} km away)"
            )
    else:
        st.write("No local supplier data found for this region yet.")

    st.subheader("📅 Follow-up")
    st.write(f"Re-check this crop around **{report.next_check_date}**. Case ID: `{report.case_id}`")

    render_trace(report.trace)


def main() -> None:
    render_header()
    submitted, description, photo, farmer_id, region = render_input_form()

    if not submitted:
        return

    if not description.strip():
        st.error("Please describe what you're seeing before submitting.")
        return

    image_path = None
    if photo is not None:
        suffix = os.path.splitext(photo.name)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(photo.getbuffer())
            image_path = tmp.name

    orchestrator = get_orchestrator()
    with st.spinner("Running multi-agent diagnosis pipeline..."):
        report = orchestrator.process_case(
            description=description,
            farmer_id=farmer_id or "anonymous",
            region=region or "default",
            image_path=image_path,
        )

    if image_path:
        os.unlink(image_path)  
    render_report(report)


if __name__ == "__main__":
    main()
